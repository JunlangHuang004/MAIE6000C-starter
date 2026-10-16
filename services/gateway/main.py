"""Private-demo form login; Nginx checks signed sessions before proxying the API."""
import hashlib
import hmac
import os
import secrets
import time
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

COOKIE = "__Host-nutrichat_session"
SESSION_SECONDS = 8 * 60 * 60


def create_app(username: str, password_hash: str, signing_key: str, origin: str) -> FastAPI:
    if not username or len(signing_key) < 32 or not origin.startswith("https://"):
        raise ValueError("Gateway requires a username, strong signing key and HTTPS origin")
    salt_hex, expected_hash = password_hash.split(":")
    salt = bytes.fromhex(salt_hex)
    if len(salt) < 16 or len(bytes.fromhex(expected_hash)) != 32:
        raise ValueError("Invalid password hash")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def signature(payload: str) -> str:
        return hmac.new(signing_key.encode(), payload.encode(), hashlib.sha256).hexdigest()

    def valid_session(token: str) -> bool:
        try:
            expires, nonce, supplied_signature = token.split(".")
            payload = expires + "." + nonce
            return (time.time() < int(expires) <= time.time() + SESSION_SECONDS
                    and len(nonce) == 32
                    and hmac.compare_digest(signature(payload), supplied_signature))
        except (ValueError, TypeError):
            return False

    @app.middleware("http")
    async def private_responses(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.get("/health/live")
    def health():
        return {"status": "ok"}

    @app.get("/verify")
    def verify(request: Request):
        return Response(status_code=204 if valid_session(request.cookies.get(COOKIE, "")) else 401)

    def login_page(error: bool = False) -> HTMLResponse:
        message = '<p class="error" role="alert">账号或密码不正确，请重试。</p>' if error else ""
        return HTMLResponse("""<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>登录 NutriChat</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7f5;color:#17342b;
font:16px system-ui,sans-serif;display:grid;min-height:100dvh;place-items:center;padding:24px}
main{width:100%;max-width:420px;background:white;border:1px solid #dce7df;
border-radius:20px;padding:32px;box-shadow:0 12px 40px #17342b0d}
h1{font-size:30px;margin:0 0 10px}p{color:#53665e;line-height:1.6}
label{display:block;margin-top:20px;font-weight:600}input{display:block;width:100%;
padding:13px;margin-top:8px;border:1px solid #9bad9f;border-radius:8px;font:inherit}
button{width:100%;padding:14px;margin-top:26px;background:#176348;color:white;
border:0;border-radius:8px;font:inherit;font-weight:600;cursor:pointer}
input:focus,button:focus{outline:3px solid #a0d7bb;outline-offset:2px}
.error{color:#a52323}.note{font-size:13px;margin-bottom:0}
</style></head><body><main><h1>NutriChat</h1><p>登录后，开始记录和查看你的餐食估算。</p>
""" + message + """<form method="post" action="/login">
<label for="username">账号</label><input id="username" name="username"
autocomplete="username" required maxlength="100" autofocus>
<label for="password">密码</label><input id="password" name="password" type="password"
autocomplete="current-password" required maxlength="256">
<button type="submit">登录</button></form><p class="note">共享演示账号 · 登录有效期 8 小时</p>
</main></body></html>""", status_code=401 if error else 200)

    @app.get("/login")
    def get_login(request: Request):
        if valid_session(request.cookies.get(COOKIE, "")):
            return RedirectResponse("/app", status_code=303)
        return login_page()

    @app.post("/login")
    async def login(request: Request):
        if request.headers.get("origin") != origin:
            return Response(status_code=403)
        if request.headers.get("content-type", "").split(";")[0] != (
            "application/x-www-form-urlencoded"
        ):
            return Response(status_code=415)
        body = await request.body()
        if len(body) > 4096:
            return Response(status_code=413)
        try:
            fields = parse_qs(body.decode(), max_num_fields=4)
            supplied_user = fields.get("username", [""])[0]
            password = fields.get("password", [""])[0]
        except (ValueError, UnicodeDecodeError):
            return Response(status_code=400)
        if len(password) > 256 or len(supplied_user) > 100:
            return login_page(True)
        candidate = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32).hex()
        password_ok = hmac.compare_digest(candidate, expected_hash)
        user_ok = hmac.compare_digest(supplied_user.encode(), username.encode())
        if not (password_ok and user_ok):
            return login_page(True)
        payload = str(int(time.time()) + SESSION_SECONDS) + "." + secrets.token_hex(16)
        response = RedirectResponse("/app", status_code=303)
        response.set_cookie(COOKIE, payload + "." + signature(payload),
                            max_age=SESSION_SECONDS, secure=True, httponly=True,
                            samesite="strict", path="/")
        return response

    @app.post("/logout")
    def logout(request: Request):
        if request.headers.get("origin") != origin:
            return Response(status_code=403)
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(COOKIE, secure=True, httponly=True, samesite="strict", path="/")
        return response

    return app


def from_environment() -> FastAPI:
    return create_app(os.environ["DEMO_USERNAME"], os.environ["DEMO_PASSWORD_HASH"],
                      os.environ["DEMO_SESSION_KEY"], os.environ["DEMO_PUBLIC_ORIGIN"])
