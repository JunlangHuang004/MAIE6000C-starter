from __future__ import annotations

from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient

from services.api.app.main import app
from services.common.db import Base, get_db, make_engine, make_session_factory
from services.common.config import get_settings


@pytest.fixture()
def db_session(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = make_engine(database_url)
    testing_session_factory = make_session_factory(engine)

    Base.metadata.create_all(bind=engine)
    session = testing_session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def auth_settings(monkeypatch):
    from services.api.app.auth import auth_limiter

    settings = get_settings()
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    monkeypatch.setattr(settings, "auth_public_origin", "http://testserver")
    monkeypatch.setattr(settings, "auth_registration_enabled", True)
    auth_limiter.clear()
    yield settings
    auth_limiter.clear()


@pytest.fixture()
def client_factory(db_session, auth_settings):
    """Independent browser cookie jars sharing the test database, without bypassing auth."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with ExitStack() as stack:
            def create_client(**kwargs):
                kwargs.setdefault("headers", {"X-NutriChat-Request": "1"})
                return stack.enter_context(TestClient(app, **kwargs))

            yield create_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def client(client_factory):
    test_client = client_factory()
    registered = test_client.post("/auth/register", json={
        "username": "fixture_user", "password": "Synthetic-test-password-42",
    })
    assert registered.status_code == 201, registered.text
    return test_client
