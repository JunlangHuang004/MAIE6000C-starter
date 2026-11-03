import os
import secrets
import uuid

import httpx
import pytest


@pytest.fixture()
def smoke_client():
    """Use real accounts; automatic signup is intended for a disposable smoke stack."""
    base_url = os.getenv("SMOKE_BASE_URL")
    if not base_url:
        pytest.skip("SMOKE_BASE_URL not set")
    with httpx.Client(base_url=base_url, timeout=10,
                      headers={"X-NutriChat-Request": "1"}) as client:
        username = os.getenv("SMOKE_USERNAME")
        password = os.getenv("SMOKE_PASSWORD")
        if bool(username) != bool(password):
            pytest.fail("Provide both SMOKE_USERNAME and SMOKE_PASSWORD")
        if username:
            response = client.post("/auth/login", json={
                "username": username, "password": password,
            })
            assert response.status_code == 200, "Smoke account login failed"
        else:
            response = client.post("/auth/register", json={
                "username": "smoke_" + uuid.uuid4().hex[:24],
                "password": secrets.token_urlsafe(24),
            })
            assert response.status_code == 201, (
                "Enable registration in the disposable smoke stack, or provide "
                "SMOKE_USERNAME and SMOKE_PASSWORD for an existing test account"
            )
        assert client.get("/auth/me").status_code == 200, (
            "Session cookie was not accepted; HTTP smoke stacks require AUTH_COOKIE_SECURE=false"
        )
        yield client
        assert client.post("/auth/logout").status_code == 204
