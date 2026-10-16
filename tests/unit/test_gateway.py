import hashlib

import pytest
from fastapi.testclient import TestClient

from services.gateway.main import COOKIE, create_app


@pytest.fixture
def client():
    salt = bytes.fromhex("ab" * 16)
    digest = hashlib.scrypt(b"test-password", salt=salt, n=16384, r=8, p=1, dklen=32)
    app = create_app("demo", salt.hex() + ":" + digest.hex(), "k" * 32, "https://example.test")
    with TestClient(app, base_url="https://example.test", follow_redirects=False) as c:
        yield c


def login(client, password="test-password", origin="https://example.test"):
    return client.post("/login", data={"username": "demo", "password": password},
                       headers={"Origin": origin})


def test_login_session_and_logout(client):
    assert client.get("/verify").status_code == 401
    page = client.get("/login")
    assert page.status_code == 200
    assert '<form method="post" action="/login">' in page.text
    assert "www-authenticate" not in page.headers
    result = login(client)
    assert result.status_code == 303 and result.headers["location"] == "/app"
    cookie = result.headers["set-cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert client.get("/verify").status_code == 204
    assert client.get("/login").status_code == 303
    assert client.post("/logout", headers={"Origin": "https://evil.test"}).status_code == 403
    assert client.post("/logout", headers={"Origin": "https://example.test"}).status_code == 303
    assert client.get("/verify").status_code == 401


def test_wrong_password_and_cross_site_login_rejected(client):
    result = login(client, password="incorrect")
    assert result.status_code == 401 and "role=\"alert\"" in result.text
    assert "www-authenticate" not in result.headers
    assert "set-cookie" not in result.headers
    assert login(client, origin="https://evil.test").status_code == 403
    assert client.get("/verify").status_code == 401


def test_forged_and_expired_sessions_rejected(client, monkeypatch):
    login(client)
    token = client.cookies.get(COOKIE)
    client.cookies.clear()
    client.cookies.set(COOKIE, token + "x")
    assert client.get("/verify").status_code == 401
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    monkeypatch.setattr("services.gateway.main.time.time", lambda: int(token.split(".")[0]) + 1)
    assert client.get("/verify").status_code == 401


def test_gateway_fails_closed_without_valid_configuration():
    with pytest.raises(ValueError):
        create_app("demo", "bad", "weak", "http://example.test")
