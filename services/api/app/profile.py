"""Private, versioned account profiles for deterministic daily references."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.api.app.auth import get_current_user
from services.common.db import get_db
from services.common.models import User, UserProfile, utcnow
from services.common.schemas import ProfileRead, ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])
_CONFLICT_MESSAGE = "Your profile has changed. Reload it before saving again."


def _profile_response(profile: UserProfile | None) -> ProfileResponse:
    if profile is None:
        return ProfileResponse(profile=None, reference=None)
    from services.common.personalization import calculate_reference

    return ProfileResponse(
        profile=ProfileRead.model_validate(profile), reference=calculate_reference(profile),
    )


@router.get("", response_model=ProfileResponse)
def read_profile(
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
) -> ProfileResponse:
    return _profile_response(db.get(UserProfile, user.id))


@router.put("", response_model=ProfileResponse)
def save_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    values = payload.model_dump(exclude={"revision"})
    now = utcnow()
    if payload.revision == 0:
        # The primary key prevents concurrent first writes from creating duplicates.
        profile = UserProfile(
            user_id=user.id, **values, revision=1, created_at=now, updated_at=now,
        )
        db.add(profile)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=_CONFLICT_MESSAGE) from exc
    else:
        result = db.execute(
            update(UserProfile).where(
                UserProfile.user_id == user.id,
                UserProfile.revision == payload.revision,
            ).values(**values, revision=payload.revision + 1, updated_at=now),
            execution_options={"synchronize_session": False},
        )
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail=_CONFLICT_MESSAGE)
        db.commit()
        profile = db.get(UserProfile, user.id)
    db.refresh(profile)
    return _profile_response(profile)
