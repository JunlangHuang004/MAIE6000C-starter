"""Private profile persistence, strict writes and concurrent browser edits."""

import json

import pytest
from sqlalchemy import select

from services.common.db import make_session_factory
from services.common.models import Job, UserProfile


PASSWORD = "Synthetic-profile-password-42"
PROFILE = {
    "age_years": 30,
    "height_cm": 175,
    "weight_kg": 70,
    "sex": "male",
    "goal": "gain_muscle",
    "activity_level": "moderate",
    "revision": 0,
}


def register(browser, username):
    response = browser.post("/auth/register", json={
        "username": username, "password": PASSWORD,
    })
    assert response.status_code == 201, response.text
    return response.json()


def save(browser, **changes):
    return browser.put("/profile", json={**PROFILE, **changes})


def test_profile_is_optional_and_reading_does_not_create_one(client, db_session):
    response = client.get("/profile")
    assert response.status_code == 200
    assert response.json() == {"profile": None, "reference": None}
    assert "no-store" in response.headers["cache-control"]
    assert db_session.query(UserProfile).count() == 0
    # A missing profile must not block the existing meal workflow.
    assert client.post("/analyses", json={"food_text": "100g egg"}).status_code == 201


def test_profile_and_reference_survive_a_new_database_session(client, db_session):
    user_id = client.get("/auth/me").json()["id"]
    response = save(client)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert set(saved) == {"profile", "reference"}
    assert saved["profile"]["revision"] == 1
    assert saved["profile"]["updated_at"].endswith("Z")
    assert set(saved["profile"]) == set(PROFILE) | {"updated_at"}
    for field, value in PROFILE.items():
        if field != "revision":
            assert saved["profile"][field] == value
    assert saved["reference"]["status"] == "estimated"
    assert "no-store" in response.headers["cache-control"]
    assert client.get("/profile").json() == saved
    session_factory = make_session_factory(db_session.get_bind())
    with session_factory() as fresh_db:
        persisted = fresh_db.get(UserProfile, user_id)
        assert persisted.weight_kg == 70
        assert persisted.revision == 1
        assert fresh_db.query(UserProfile).count() == 1
    assert db_session.query(Job).count() == 0


def test_update_recomputes_reference_without_creating_another_profile(client, db_session):
    first = save(client).json()
    second = save(client, revision=1, weight_kg=80, goal="lose_fat")
    assert second.status_code == 200, second.text
    updated = second.json()
    assert updated["profile"]["weight_kg"] == 80
    assert updated["profile"]["goal"] == "lose_fat"
    assert updated["profile"]["revision"] == 2
    assert updated["reference"] != first["reference"]
    assert updated["profile"]["updated_at"] >= first["profile"]["updated_at"]
    assert client.get("/profile").json() == updated
    assert db_session.query(UserProfile).count() == 1


@pytest.mark.parametrize("method", ["get", "put"])
def test_anonymous_profile_requests_are_rejected(client_factory, db_session, method):
    browser = client_factory()
    response = browser.get("/profile") if method == "get" else save(browser)
    assert response.status_code == 401
    assert "no-store" in response.headers["cache-control"]
    assert db_session.query(UserProfile).count() == 0


def test_profile_isolated_between_accounts_and_cannot_be_selected_by_headers_or_query(
        client_factory, db_session):
    alice, bob, anonymous = client_factory(), client_factory(), client_factory()
    first_user = register(alice, "profile_alice")
    second_user = register(bob, "profile_bob")
    first = save(alice).json()
    assert bob.get("/profile").json() == {"profile": None, "reference": None}
    second = save(bob, age_years=45, height_cm=162, weight_kg=60, sex="female").json()
    assert first["reference"] != second["reference"]
    spoof = {"X-User-Id": first_user["id"], "X-Forwarded-User": first_user["username"]}
    path = f"/profile?user_id={first_user['id']}"
    assert bob.get(path, headers=spoof).json() == second
    assert anonymous.get(path, headers=spoof).status_code == 401
    edited = bob.put(path, headers=spoof, json={**PROFILE, "revision": 1, "age_years": 55})
    assert edited.status_code == 200
    assert edited.json()["profile"]["age_years"] == 55
    assert bob.get("/profile").json() == edited.json()
    assert bob.get(f"/profile/{first_user['id']}").status_code == 404
    assert alice.get("/profile").json() == first
    owners = db_session.execute(select(UserProfile.user_id)).scalars().all()
    assert set(owners) == {first_user["id"], second_user["id"]}


@pytest.mark.parametrize("field", ["user_id", "owner_id", "id", "calories", "reference"])
def test_profile_cannot_mass_assign_identity_or_computed_values(client, db_session, field):
    response = save(client, **{field: "private-input-must-not-be-echoed"})
    assert response.status_code == 422
    assert "private-input-must-not-be-echoed" not in response.text
    assert db_session.query(UserProfile).count() == 0


def test_profile_mutation_requires_csrf_header_and_same_origin(client, db_session):
    client.headers.pop("X-NutriChat-Request")
    assert save(client).status_code == 403
    client.headers["X-NutriChat-Request"] = "1"
    blocked = client.put("/profile", json=PROFILE, headers={"Origin": "https://attacker.test"})
    assert blocked.status_code == 403
    assert db_session.query(UserProfile).count() == 0
    accepted = client.put("/profile", json=PROFILE, headers={"Origin": "http://testserver"})
    assert accepted.status_code == 200


def test_logout_hides_profile_and_login_restores_the_same_saved_data(client_factory):
    browser = client_factory()
    register(browser, "profile_alice")
    saved = save(browser).json()
    assert browser.post("/auth/logout").status_code == 204
    assert browser.get("/profile").status_code == 401
    assert save(browser, revision=1, weight_kg=90).status_code == 401
    assert browser.post("/auth/login", json={
        "username": "profile_alice", "password": PASSWORD,
    }).status_code == 200
    assert browser.get("/profile").json() == saved


@pytest.mark.parametrize("revision", [0, 2, 999])
def test_stale_or_future_revision_never_overwrites_a_saved_profile(client, db_session, revision):
    saved = save(client).json()
    response = save(client, revision=revision, weight_kg=95)
    assert response.status_code == 409
    assert "no-store" in response.headers["cache-control"]
    assert client.get("/profile").json() == saved
    assert db_session.query(UserProfile).count() == 1


def test_nonzero_revision_cannot_create_missing_profile(client, db_session):
    assert save(client, revision=1).status_code == 409
    assert db_session.query(UserProfile).count() == 0
    assert save(client).status_code == 200  # Rollback leaves the session usable.


def test_two_browser_edits_of_same_account_cannot_silently_overwrite(client_factory):
    first, second = client_factory(), client_factory()
    register(first, "profile_alice")
    assert second.post("/auth/login", json={
        "username": "profile_alice", "password": PASSWORD,
    }).status_code == 200
    original = save(first).json()
    assert second.get("/profile").json() == original
    winner = save(first, revision=1, weight_kg=72).json()
    stale = save(second, revision=1, weight_kg=68)
    assert stale.status_code == 409
    assert second.get("/profile").json() == winner
    retry = save(second, revision=2, weight_kg=68)
    assert retry.status_code == 200
    assert retry.json()["profile"]["revision"] == 3
    assert first.get("/profile").json() == retry.json()


@pytest.mark.parametrize("changes", [
    {"age_years": 17}, {"age_years": "30"}, {"age_years": 30.5},
    {"height_cm": "175"}, {"height_cm": True}, {"weight_kg": False},
    {"weight_kg": 251}, {"sex": "unknown"}, {"goal": "maintain"},
    {"activity_level": "extreme"}, {"revision": True}, {"revision": "1"},
])
def test_invalid_profile_edits_do_not_mutate_existing_record(client, changes):
    saved = save(client).json()
    rejected = save(client, **{"revision": 1, **changes})
    assert rejected.status_code == 422
    assert client.get("/profile").json() == saved


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_json_numeric_input_returns_safe_validation_error(client, value):
    response = client.put(
        "/profile", content=json.dumps({**PROFILE, "weight_kg": value}),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert all(set(error) == {"loc", "msg", "type"} for error in response.json()["detail"])
    assert client.get("/profile").json() == {"profile": None, "reference": None}


def test_guarded_profile_can_be_saved_without_generating_a_restricted_target(client):
    response = save(client, weight_kg=45, height_cm=175, goal="lose_fat")
    assert response.status_code == 200
    assert response.json()["reference"]["status"] == "needs_review"
    assert client.get("/profile").json() == response.json()


def test_daily_references_do_not_send_profile_to_qwen_or_queue_ai_work(
        client, db_session, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Profile calculations must not call the AI service or Qwen")

    monkeypatch.setattr("services.ai.app.qwen.analyze_with_qwen", forbidden)
    monkeypatch.setattr("httpx.post", forbidden)
    assert save(client).status_code == 200
    assert client.get("/profile").json()["reference"]["status"] == "estimated"
    assert db_session.query(Job).count() == 0
