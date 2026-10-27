"""Local accounts and opaque, revocable browser sessions.

Identity always comes from a session looked up in the database. Proxy headers and
client-supplied user IDs never establish ownership.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from collections import OrderedDict, deque
from datetime import timedelta
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.common.config import get_settings
from services.common.db import get_db
from services.common.models import AuthSession, User, utcnow
from services.common.schemas import AuthCredentials, UserRead

COOKIE_NAME = "nutrichat_session"
SCRYPT_N = 32768
SCRYPT_R = 8
SCRYPT_P = 3
SCRYPT_MAXMEM = 128 * 1024 * 1024
router = APIRouter(prefix="/auth", tags=["accounts"])


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not 10 <= len(password) <= 128:
        raise ValueError("Password must contain 10 to 128 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
        maxmem=SCRYPT_MAXMEM, dklen=64,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    if not isinstance(password, str) or not 10 <= len(password) <= 128:
        return False
    try:
        algorithm, n, r, p, salt_hex, digest_hex = encoded.split("$")
        # A corrupted hash must not turn into an unbounded allocation/work request.
        if (algorithm, n, r, p) != ("scrypt", str(SCRYPT_N), str(SCRYPT_R), str(SCRYPT_P)):
            return False
        if len(salt_hex) != 32 or len(digest_hex) != 128:
            return False
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
            maxmem=SCRYPT_MAXMEM, dklen=64,
        )
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False


# Unknown users still perform the normal password verification work.
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


class AuthRateLimiter:
    """Bounded single-process guard; deployments with replicas need a shared limiter."""

    def __init__(self, max_keys: int = 4096):
        self.max_keys = max_keys
        self._events: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def check(self, key: str, limit: int, window: int) -> None:
        now = monotonic()
        with self._lock:
            events = self._events.setdefault(key, deque())
            self._events.move_to_end(key)
            while events and events[0] <= now - window:
                events.popleft()
            if len(events) >= limit:
                raise HTTPException(
                    status_code=429, detail="Too many attempts. Please try again later.",
                    headers={"Retry-After": str(max(1, int(events[0] + window - now) + 1))},
                )
            events.append(now)
            while len(self._events) > self.max_keys:
                self._events.popitem(last=False)


auth_limiter = AuthRateLimiter()


def _limit_attempts(request: Request, action: str, username: str) -> None:
    # Do not trust X-Forwarded-For from callers. A proxy should enforce its own
    # client-IP limit; this in-process layer may count all proxy traffic together.
    address = request.client.host if request.client else "unknown"
    if action == "register":
        auth_limiter.check(f"register:ip:{address}", 5, 3600)
    else:
        auth_limiter.check(f"login:ip:{address}", 20, 300)
        auth_limiter.check(f"login:user:{username}", 10, 300)


def _cookie_digest(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 128:
        return None
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    digest = _cookie_digest(request)
    if digest is None:
        return None
    return db.execute(
        select(User).join(AuthSession, AuthSession.user_id == User.id).where(
            AuthSession.token_hash == digest,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utcnow(),
        )
    ).scalar_one_or_none()


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return user


def _revoke_cookie_session(request: Request, db: Session) -> None:
    digest = _cookie_digest(request)
    if digest is not None:
        db.execute(update(AuthSession).where(
            AuthSession.token_hash == digest, AuthSession.revoked_at.is_(None),
        ).values(revoked_at=utcnow()))


def _start_session(user: User, request: Request, response: Response, db: Session) -> None:
    settings = get_settings()
    now = utcnow()
    _revoke_cookie_session(request, db)
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(), user_id=user.id,
        created_at=now, expires_at=now + timedelta(seconds=settings.auth_session_ttl_seconds),
    ))
    db.commit()
    response.set_cookie(
        COOKIE_NAME, token, max_age=settings.auth_session_ttl_seconds, path="/",
        secure=settings.auth_cookie_secure, httponly=True, samesite="strict",
    )


@router.get("/config")
def auth_config() -> dict[str, bool]:
    return {"registration_enabled": get_settings().auth_registration_enabled}


@router.post("/register", response_model=UserRead, status_code=201)
def register(
    payload: AuthCredentials, request: Request, response: Response, db: Session = Depends(get_db),
) -> UserRead:
    if not get_settings().auth_registration_enabled:
        raise HTTPException(status_code=403, detail="Registration is not currently available.")
    _limit_attempts(request, "register", payload.username)
    user = User(username=payload.username, password_hash=hash_password(
        payload.password.get_secret_value(),
    ))
    db.add(user)
    try:
        db.flush()
        _start_session(user, request, response, db)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account could not be created with these details.",
        ) from exc
    return UserRead.model_validate(user)


@router.post("/login", response_model=UserRead)
def login(
    payload: AuthCredentials, request: Request, response: Response, db: Session = Depends(get_db),
) -> UserRead:
    _limit_attempts(request, "login", payload.username)
    user = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    valid_password = verify_password(
        payload.password.get_secret_value(), user.password_hash if user else _DUMMY_PASSWORD_HASH,
    )
    if user is None or not valid_password:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    _start_session(user, request, response, db)
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)


@router.post("/logout", status_code=204, response_class=Response, response_model=None)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    _revoke_cookie_session(request, db)
    db.commit()
    response.delete_cookie(
        COOKIE_NAME, path="/", secure=get_settings().auth_cookie_secure,
        httponly=True, samesite="strict",
    )
    response.status_code = 204
    return response
