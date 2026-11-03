"""Exercise public account/session contracts and real database ownership checks."""

import hashlib
from datetime import timedelta

import pytest
from sqlalchemy import select

from services.api.app.auth import COOKIE_NAME, verify_password
from services.common.models import Analysis, AuthSession, Case, Job, User, utcnow


PASSWORD = "Synthetic-test-password-42"


def register(client, username="alice"):
    response = client.post("/auth/register", json={"username": username, "password": PASSWORD})
    assert response.status_code == 201, response.text
    assert set(response.json()) == {"id", "username"}
    return response.json()


def create_meal(client, **extra):
    response = client.post("/analyses", json={"food_text": "100g egg", **extra})
    assert response.status_code == 201, response.text
    return response.json()


def create_case(client, **extra):
    response = client.post("/cases", json={
        "title": "Synthetic support case", "description": "Synthetic case for account isolation.",
        **extra,
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_registration_logs_in_and_passwords_are_salted(db_session, client_factory):
    alice, bob = client_factory(), client_factory()
    first = register(alice, "Alice")
    second = register(bob, "bob")
    assert first["username"] == "alice"
    assert alice.get("/auth/me").json() == first
    assert bob.get("/auth/me").json() == second
    assert first["id"] != second["id"]
    users = db_session.execute(select(User)).scalars().all()
    assert len(users) == 2
    assert users[0].password_hash != users[1].password_hash
    for user in users:
        assert PASSWORD not in user.password_hash
        assert verify_password(PASSWORD, user.password_hash)
        assert not verify_password("wrong-password", user.password_hash)


def test_username_is_case_insensitive_at_signup_and_login(client_factory, db_session):
    client = client_factory()
    first = register(client, "Alice")
    duplicate = client.post("/auth/register", json={"username": "ALICE", "password": PASSWORD})
    assert duplicate.status_code == 409
    assert db_session.query(User).count() == 1
    assert client.post("/auth/logout").status_code == 204
    logged_in = client.post("/auth/login", json={"username": "ALICE", "password": PASSWORD})
    assert logged_in.status_code == 200
    assert logged_in.json() == first


@pytest.mark.parametrize("username", [
    "ab", "a" * 33, "name@example.com", "user name", "你好abc", "a-b",
])
def test_invalid_usernames_do_not_create_accounts(client_factory, db_session, username):
    response = client_factory().post("/auth/register", json={
        "username": username, "password": PASSWORD,
    })
    assert response.status_code == 422
    assert db_session.query(User).count() == 0
    assert db_session.query(AuthSession).count() == 0


@pytest.mark.parametrize("password", ["short1234", "x" * 129])
def test_password_length_validation(client_factory, db_session, password):
    response = client_factory().post("/auth/register", json={
        "username": "alice", "password": password,
    })
    assert response.status_code == 422
    assert password not in response.text
    assert db_session.query(User).count() == 0


def test_bad_login_does_not_reveal_whether_username_exists(client_factory):
    browser = client_factory()
    register(browser)
    anonymous = client_factory()
    wrong = anonymous.post("/auth/login", json={
        "username": "alice", "password": "incorrect-password",
    })
    missing = anonymous.post("/auth/login", json={
        "username": "nobody", "password": "incorrect-password",
    })
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()
    assert COOKIE_NAME not in anonymous.cookies
    assert anonymous.get("/auth/me").status_code == 401


def test_session_cookie_is_opaque_hashed_in_database_and_private(client_factory, db_session):
    client = client_factory()
    registered = client.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    token = client.cookies.get(COOKIE_NAME)
    assert token and len(token) >= 32
    session = db_session.execute(select(AuthSession)).scalar_one()
    assert session.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in session.token_hash
    assert session.user_id == registered.json()["id"]
    assert session.expires_at > session.created_at
    cookie = registered.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/" in cookie
    assert "secure" not in cookie  # Explicit HTTP-only test configuration.
    assert "no-store" in client.get("/auth/me").headers.get("cache-control", "")


def test_production_cookie_is_secure(client_factory, auth_settings, monkeypatch):
    monkeypatch.setattr(auth_settings, "auth_cookie_secure", True)
    monkeypatch.setattr(auth_settings, "auth_public_origin", "https://testserver")
    client = client_factory(base_url="https://testserver")
    response = client.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    assert response.status_code == 201
    assert "secure" in response.headers["set-cookie"].lower()
    assert client.get("/auth/me").status_code == 200


def test_logout_revokes_stolen_token_and_clears_browser_cookie(client_factory, db_session):
    client = client_factory()
    register(client)
    token = client.cookies.get(COOKIE_NAME)
    assert client.post("/auth/logout").status_code == 204
    assert COOKIE_NAME not in client.cookies
    assert client.get("/auth/me").status_code == 401
    replay = client_factory(headers={"Cookie": f"{COOKIE_NAME}={token}"})
    assert replay.get("/auth/me").status_code == 401
    session = db_session.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
    assert session is None or session.revoked_at is not None


def test_login_rotates_and_revokes_previous_cookie(client_factory):
    client = client_factory()
    register(client)
    previous = client.cookies.get(COOKIE_NAME)
    response = client.post("/auth/login", json={"username": "alice", "password": PASSWORD})
    assert response.status_code == 200
    assert client.cookies.get(COOKIE_NAME) != previous
    replay = client_factory(headers={"Cookie": f"{COOKIE_NAME}={previous}"})
    assert replay.get("/auth/me").status_code == 401
    assert client.get("/auth/me").status_code == 200


def test_expired_session_cannot_read_or_write(client_factory, db_session):
    client = client_factory()
    register(client)
    row = db_session.execute(select(AuthSession)).scalar_one()
    row.expires_at = utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert client.get("/auth/me").status_code == 401
    assert client.get("/analyses").status_code == 401
    assert client.post("/analyses", json={"food_text": "100g egg"}).status_code == 401
    assert db_session.query(Analysis).count() == 0


@pytest.mark.parametrize("path", ["/auth/me", "/analyses", "/analyses/missing",
                                  "/cases", "/cases/missing", "/jobs/1"])
def test_anonymous_reads_are_rejected(client_factory, path):
    assert client_factory().get(path).status_code == 401


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/analyses", {"food_text": "100g egg"}),
    ("post", "/cases", {"title": "A case", "description": "A valid synthetic case description"}),
    ("patch", "/analyses/missing", {"food_text": "100g egg", "revision": 1}),
    ("post", "/analyses/missing/reply", {"message": "100g egg", "revision": 1}),
    ("post", "/analyses/missing/mode", {"mode": "basic", "revision": 1}),
    ("post", "/analyses/missing/confirm", {"revision": 1}),
])
def test_anonymous_writes_are_rejected(client_factory, method, path, payload):
    assert getattr(client_factory(), method)(path, json=payload).status_code == 401


def test_public_health_and_login_page_remain_available(client_factory):
    client = client_factory()
    for path in ("/", "/health/live", "/health/ready", "/login", "/auth/config", "/foods"):
        assert client.get(path).status_code == 200
    response = client.get("/app", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_users_only_list_their_own_meals_and_cases(client_factory, db_session):
    alice, bob = client_factory(), client_factory()
    alice_user, bob_user = register(alice, "alice"), register(bob, "bob")
    alice_meal, bob_meal = create_meal(alice), create_meal(bob)
    alice_case, bob_case = create_case(alice), create_case(bob)
    for client, user, meal, case in ((alice, alice_user, alice_meal, alice_case),
                                     (bob, bob_user, bob_meal, bob_case)):
        assert [row["id"] for row in client.get("/analyses").json()] == [meal["analysis"]["id"]]
        assert [row["id"] for row in client.get("/cases").json()] == [case["case"]["id"]]
        assert db_session.get(Analysis, meal["analysis"]["id"]).user_id == user["id"]
        assert db_session.get(Case, case["case"]["id"]).user_id == user["id"]


@pytest.mark.parametrize("operation", ["read", "patch", "reply", "mode", "confirm", "job"])
def test_other_user_cannot_read_or_change_meal(client_factory, db_session, operation):
    owner, stranger = client_factory(), client_factory()
    register(owner, "alice")
    register(stranger, "bob")
    created = create_meal(owner)
    analysis_id = created["analysis"]["id"]
    row = db_session.get(Analysis, analysis_id)
    row.status = "completed"
    row.calories, row.protein_g, row.fat_g, row.carbs_g = 155, 13, 11, 1.1
    db_session.commit()
    path = f"/analyses/{analysis_id}"
    original = owner.get(path).json()
    mutations = {
        "read": lambda: stranger.get(path),
        "patch": lambda: stranger.patch(path, json={"food_text": "200g egg", "revision": 1}),
        "reply": lambda: stranger.post(path + "/reply", json={
            "message": "200g egg", "revision": 1,
        }),
        "mode": lambda: stranger.post(path + "/mode", json={"mode": "basic", "revision": 1}),
        "confirm": lambda: stranger.post(path + "/confirm", json={"revision": 1}),
        "job": lambda: stranger.get(f"/jobs/{created['job']['id']}"),
    }
    assert mutations[operation]().status_code == 404
    assert owner.get(path).json() == original
    assert db_session.query(Job).count() == 1
    assert owner.get(f"/jobs/{created['job']['id']}").status_code == 200


def test_other_user_cannot_read_case_or_its_job(client_factory):
    owner, stranger = client_factory(), client_factory()
    register(owner, "alice")
    register(stranger, "bob")
    created = create_case(owner)
    for path in (f"/cases/{created['case']['id']}", f"/jobs/{created['job']['id']}"):
        assert stranger.get(path).status_code == 404
        assert owner.get(path).status_code == 200


@pytest.mark.parametrize("malformed_links", ["both_parents", "no_parent"])
def test_malformed_job_cannot_leak_a_foreign_record_link(
        client_factory, db_session, malformed_links):
    alice, bob = client_factory(), client_factory()
    register(alice, "alice")
    register(bob, "bob")
    alice_case = create_case(alice)["case"]
    bob_meal = create_meal(bob)["analysis"]
    job = Job(job_type="analyze_nutrition")
    if malformed_links == "both_parents":
        job.case_id = alice_case["id"]
        job.analysis_id = bob_meal["id"]
    db_session.add(job)
    db_session.commit()
    # An OR over ownership alone would expose the other user's record ID.
    assert alice.get(f"/jobs/{job.id}").status_code == 404
    assert bob.get(f"/jobs/{job.id}").status_code == 404


def test_legacy_ownerless_records_are_quarantined(client_factory, db_session):
    meal = Analysis(food_text="100g egg", status="completed", calories=155)
    case = Case(title="Legacy record", description="Shared demonstration data", status="queued")
    db_session.add_all([meal, case])
    db_session.flush()
    meal_job = Job(analysis_id=meal.id, job_type="analyze_nutrition")
    case_job = Job(case_id=case.id)
    db_session.add_all([meal_job, case_job])
    db_session.commit()
    client = client_factory()
    register(client)
    assert client.get("/analyses").json() == []
    assert client.get("/cases").json() == []
    for path in (f"/analyses/{meal.id}", f"/cases/{case.id}",
                 f"/jobs/{meal_job.id}", f"/jobs/{case_job.id}"):
        assert client.get(path).status_code == 404
    assert client.patch(f"/analyses/{meal.id}", json={
        "food_text": "200g egg", "revision": 1,
    }).status_code == 404
    assert client.post(f"/analyses/{meal.id}/confirm", json={"revision": 1}).status_code == 404
    assert client.post(f"/analyses/{meal.id}/reply", json={
        "message": "200g egg", "revision": 1,
    }).status_code == 404
    assert client.post(f"/analyses/{meal.id}/mode", json={
        "mode": "basic", "revision": 1,
    }).status_code == 404
    db_session.refresh(meal)
    assert meal.user_id is None and meal.food_text == "100g egg"


def test_client_cannot_choose_another_users_owner_id(client_factory, db_session):
    alice, bob = client_factory(), client_factory()
    first, second = register(alice, "alice"), register(bob, "bob")
    meal = create_meal(alice, user_id=second["id"], owner_id=second["id"])
    case = create_case(alice, user_id=second["id"], owner_id=second["id"])
    assert db_session.get(Analysis, meal["analysis"]["id"]).user_id == first["id"]
    assert db_session.get(Case, case["case"]["id"]).user_id == first["id"]
    assert bob.get("/analyses").json() == []
    assert bob.get("/cases").json() == []


def test_identity_headers_cannot_replace_or_override_browser_session(client_factory):
    owner = client_factory()
    user = register(owner)
    meal = create_meal(owner)
    path = f"/analyses/{meal['analysis']['id']}"
    spoofed_headers = {"X-User-Id": user["id"], "X-Forwarded-User": user["username"]}
    assert client_factory().get(path, headers=spoofed_headers).status_code == 401
    stranger = client_factory()
    register(stranger, "bob")
    assert stranger.get(path, headers=spoofed_headers).status_code == 404


@pytest.mark.parametrize("path", ["/auth/register", "/auth/login"])
def test_auth_mutations_require_request_header(client_factory, db_session, path):
    response = client_factory(headers={}).post(path, json={
        "username": "alice", "password": PASSWORD,
    })
    assert response.status_code == 403
    assert db_session.query(User).count() == 0


@pytest.mark.parametrize("origin", ["https://attacker.example", "http://testserver.evil.example",
                                    "https://testserver", "null"])
def test_cross_origin_auth_requests_are_rejected(client_factory, origin):
    response = client_factory().post("/auth/register", headers={"Origin": origin},
                                     json={"username": "alice", "password": PASSWORD})
    assert response.status_code == 403


def test_same_origin_and_header_are_accepted(client_factory):
    response = client_factory().post("/auth/register", headers={"Origin": "http://testserver"},
                                     json={"username": "alice", "password": PASSWORD})
    assert response.status_code == 201


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/analyses", {"food_text": "100g egg"}),
    ("post", "/cases", {"title": "A case", "description": "A valid synthetic case description"}),
    ("patch", "/analyses/missing", {"food_text": "100g egg", "revision": 1}),
    ("post", "/analyses/missing/reply", {"message": "100g egg", "revision": 1}),
    ("post", "/analyses/missing/mode", {"mode": "basic", "revision": 1}),
    ("post", "/analyses/missing/confirm", {"revision": 1}),
    ("post", "/auth/logout", None),
])
def test_authenticated_mutations_require_csrf_header(client, method, path, payload):
    client.headers.pop("X-NutriChat-Request")
    response = getattr(client, method)(path, json=payload)
    assert response.status_code == 403
    assert client.get("/auth/me").status_code == 200


def test_cross_origin_logged_in_requests_cannot_create_meal(client, db_session):
    response = client.post("/analyses", headers={"Origin": "https://attacker.example"},
                           json={"food_text": "100g egg"})
    assert response.status_code == 403
    assert db_session.query(Analysis).count() == 0


def test_disabled_registration_is_advertised_and_enforced(
        client_factory, auth_settings, monkeypatch, db_session):
    monkeypatch.setattr(auth_settings, "auth_registration_enabled", False)
    client = client_factory()
    assert client.get("/auth/config").json()["registration_enabled"] is False
    response = client.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    assert response.status_code == 403
    assert db_session.query(User).count() == 0


def test_login_rate_limit_blocks_repeated_attempts_even_with_case_changes(client_factory):
    client = client_factory()
    register(client)
    anonymous = client_factory()
    for index in range(10):
        response = anonymous.post("/auth/login", json={
            "username": "alice" if index % 2 else "ALICE", "password": "incorrect-password",
        })
        assert response.status_code == 401
    blocked = anonymous.post("/auth/login", json={"username": "alice", "password": PASSWORD})
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    assert anonymous.get("/auth/me").status_code == 401


def test_registration_rate_limit_ignores_spoofed_forwarded_addresses(client_factory, db_session):
    client = client_factory()
    for index in range(5):
        response = client.post("/auth/register", headers={"X-Forwarded-For": f"192.0.2.{index}"},
                               json={"username": f"synthetic_{index}", "password": PASSWORD})
        assert response.status_code == 201
    blocked = client.post("/auth/register", headers={"X-Forwarded-For": "198.51.100.1"},
                          json={"username": "synthetic_blocked", "password": PASSWORD})
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    assert db_session.query(User).count() == 5


def test_existing_account_can_login_when_registration_is_closed(
        client_factory, auth_settings, monkeypatch):
    client = client_factory()
    user = register(client)
    client.post("/auth/logout")
    monkeypatch.setattr(auth_settings, "auth_registration_enabled", False)
    response = client.post("/auth/login", json={"username": "alice", "password": PASSWORD})
    assert response.status_code == 200
    assert client.get("/auth/me").json() == user
