"""Daily records, meal aggregation and private 30-day history."""

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from services.common.db import make_session_factory
from services.common.models import Analysis, DailyRecord, Job, UserProfile


DAY = "2024-03-01"
PASSWORD = "Synthetic-tracking-password-42"


def register(browser, username):
    response = browser.post("/auth/register", json={
        "username": username, "password": PASSWORD,
    })
    assert response.status_code == 201, response.text
    return response.json()


def save(browser, day=DAY, **changes):
    return browser.put(f"/daily-records/{day}", json={
        "revision": 0, "weight_kg": 70, "manual_calories": None, **changes,
    })


def meal(db, owner, calories=500, day=DAY, status="confirmed", **changes):
    row = Analysis(
        user_id=owner, food_text="Synthetic meal", status=status,
        consumed_on=date.fromisoformat(day) if day else None,
        confirmed_at=datetime(2024, 3, 5, 4, tzinfo=timezone.utc)
        if status == "confirmed" else None,
        calories=calories, protein_g=20, carbs_g=60, fat_g=20, **changes,
    )
    db.add(row)
    db.commit()
    return row


def assert_missing(day):
    assert day["revision"] == 0
    assert day["weight_kg"] is None
    assert day["manual_calories"] is None
    assert day["meal_calories"] is None
    assert day["meal_count"] == 0
    assert day["calories"] is None
    assert day["calorie_source"] is None


def test_missing_history_is_empty_not_zero_and_reads_do_not_write(client, db_session):
    response = client.get(f"/daily-records/{DAY}")
    assert response.status_code == 200
    assert response.json()["date"] == DAY
    assert_missing(response.json())
    trend = client.get(f"/tracking?end={DAY}")
    assert trend.status_code == 200
    data = trend.json()
    assert data["timezone"] == "Asia/Hong_Kong"
    assert data["start_date"] == "2024-02-01"
    assert data["end_date"] == DAY
    assert len(data["days"]) == 30
    for day in data["days"]:
        assert_missing(day)
    assert data["summary"] == {
        "recorded_days": 0, "average_calories": None, "weight_entries": 0,
        "first_weight_kg": None, "last_weight_kg": None, "weight_change_kg": None,
    }
    assert "no-store" in response.headers["cache-control"]
    assert "no-store" in trend.headers["cache-control"]
    assert db_session.query(DailyRecord).count() == 0
    assert db_session.query(Job).count() == 0


@pytest.mark.parametrize(("end", "start"), [
    ("2024-03-01", "2024-02-01"),  # Leap day is included.
    ("2023-03-01", "2023-01-31"),
    ("2024-01-01", "2023-12-03"),
    ("2000-01-30", "2000-01-01"),
])
def test_trend_is_exactly_30_consecutive_inclusive_days(client, end, start):
    response = client.get(f"/tracking?end={end}")
    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == start
    assert data["end_date"] == end
    assert [day["date"] for day in data["days"]] == [
        (date.fromisoformat(start) + timedelta(days=index)).isoformat()
        for index in range(30)
    ]


def test_record_persists_and_weight_does_not_change_profile(client, db_session):
    user_id = client.get("/auth/me").json()["id"]
    profile = client.put("/profile", json={
        "age_years": 30, "height_cm": 175, "weight_kg": 72,
        "sex": "male", "goal": "gain_muscle", "activity_level": "moderate",
        "revision": 0,
    }).json()
    result = save(client, weight_kg=70.5, manual_calories=2150)
    assert result.status_code == 200, result.text
    saved = result.json()
    assert saved["revision"] == 1
    assert saved["weight_kg"] == 70.5
    assert saved["calories"] == 2150
    assert saved["calorie_source"] == "manual"
    assert "no-store" in result.headers["cache-control"]
    assert client.get(f"/daily-records/{DAY}").json() == saved
    factory = make_session_factory(db_session.get_bind())
    with factory() as fresh:
        row = fresh.get(DailyRecord, (user_id, date.fromisoformat(DAY)))
        assert row.weight_kg == 70.5
        assert row.manual_calories == 2150
        assert row.revision == 1
        assert fresh.get(UserProfile, user_id).weight_kg == 72
    assert client.get("/profile").json() == profile
    assert db_session.query(Job).count() == 0


def test_auto_aggregation_uses_consumed_date_and_only_owned_confirmed_meals(
        client_factory, db_session):
    alice, bob = client_factory(), client_factory()
    a, b = register(alice, "tracking_alice"), register(bob, "tracking_bob")
    meal(db_session, a["id"], 500)
    meal(db_session, a["id"], 250.5)
    meal(db_session, a["id"], 900, day="2024-03-02")
    meal(db_session, a["id"], 800, day=None)
    for state in ["queued", "needs_input", "completed", "failed"]:
        meal(db_session, a["id"], 1000, status=state)
    meal(db_session, b["id"], 1800)
    meal(db_session, None, 9999)
    record = alice.get(f"/daily-records/{DAY}").json()
    assert record["calories"] == 750.5
    assert record["meal_calories"] == 750.5
    assert record["meal_count"] == 2
    assert record["calorie_source"] == "meals"
    assert record["weight_kg"] is None
    assert record["revision"] == 0
    assert bob.get(f"/daily-records/{DAY}").json()["calories"] == 1800
    assert alice.get("/daily-records/2024-03-05").json()["calories"] is None
    data = alice.get(f"/tracking?end={DAY}").json()
    assert data["days"][-1] == record
    assert data["summary"]["recorded_days"] == 1
    assert data["summary"]["average_calories"] == 750.5


def test_manual_total_overrides_meals_and_clearing_restores_live_aggregate(client, db_session):
    owner = client.get("/auth/me").json()["id"]
    meal(db_session, owner, 600)
    override = save(client, manual_calories=1800).json()
    assert override["calories"] == 1800
    assert override["meal_calories"] == 600
    assert override["meal_count"] == 1
    assert override["calorie_source"] == "manual"
    meal(db_session, owner, 200)
    latest = client.get(f"/daily-records/{DAY}").json()
    assert latest["calories"] == 1800
    assert latest["meal_calories"] == 800
    cleared = save(client, revision=1, manual_calories=None, weight_kg=None).json()
    assert cleared["revision"] == 2
    assert cleared["calories"] == 800
    assert cleared["calorie_source"] == "meals"
    assert cleared["weight_kg"] is None
    assert db_session.query(DailyRecord).count() == 1
    assert client.get(f"/daily-records/{DAY}").json() == cleared


def test_empty_record_retains_revision_without_inventing_values(client):
    saved = save(client).json()
    assert saved["calories"] is None
    cleared = save(client, revision=1, weight_kg=None).json()
    assert cleared["revision"] == 2
    assert cleared["calories"] is None
    assert cleared["calorie_source"] is None
    assert cleared["weight_kg"] is None
    summary = client.get(f"/tracking?end={DAY}").json()["summary"]
    assert summary["recorded_days"] == 0
    assert summary["weight_entries"] == 0


def test_summary_uses_observed_days_and_first_last_measurements_without_filling_gaps(
        client, db_session):
    owner = client.get("/auth/me").json()["id"]
    # Outside the selected 30-day range must not affect summaries.
    save(client, "2024-01-31", manual_calories=5000, weight_kg=99)
    save(client, "2024-02-01", manual_calories=0, weight_kg=None)
    save(client, "2024-02-03", manual_calories=2000, weight_kg=70)
    meal(db_session, owner, 1000, "2024-02-07")
    save(client, "2024-02-15", weight_kg=69)
    save(client, "2024-02-27", weight_kg=70.2)
    meal(db_session, owner, 9999, "2024-03-02")
    response = client.get(f"/tracking?end={DAY}").json()
    summary = response["summary"]
    assert summary == {
        "recorded_days": 3, "average_calories": 1000,
        "weight_entries": 3, "first_weight_kg": 70,
        "last_weight_kg": 70.2, "weight_change_kg": 0.2,
    }
    days = {day["date"]: day for day in response["days"]}
    assert days["2024-02-01"]["calories"] == 0
    assert days["2024-02-01"]["calorie_source"] == "manual"
    assert days["2024-02-02"]["calories"] is None
    assert days["2024-02-07"]["weight_kg"] is None
    assert days["2024-02-28"]["weight_kg"] is None
    assert days["2024-02-29"]["calories"] is None


def test_single_measurement_has_no_weight_change(client):
    save(client)
    summary = client.get(f"/tracking?end={DAY}").json()["summary"]
    assert summary["weight_entries"] == 1
    assert summary["first_weight_kg"] == summary["last_weight_kg"] == 70
    assert summary["weight_change_kg"] is None


def test_daily_records_are_separate_per_user_and_date_even_with_spoofed_owner(client_factory):
    alice, bob, anonymous = client_factory(), client_factory(), client_factory()
    a = register(alice, "tracking_alice")
    register(bob, "tracking_bob")
    first = save(alice, manual_calories=1900).json()
    second = save(bob, weight_kg=85, manual_calories=2500).json()
    next_day = save(alice, "2024-03-02", weight_kg=71).json()
    spoof = {"X-User-Id": a["id"], "X-Forwarded-User": a["username"]}
    path = f"/daily-records/{DAY}?user_id={a['id']}"
    assert bob.get(path, headers=spoof).json() == second
    assert anonymous.get(path, headers=spoof).status_code == 401
    updated = bob.put(path, headers=spoof, json={
        "revision": 1, "weight_kg": 84, "manual_calories": 2200,
    })
    assert updated.status_code == 200
    assert alice.get(f"/daily-records/{DAY}").json() == first
    assert alice.get("/daily-records/2024-03-02").json() == next_day
    data = bob.get(f"/tracking?end={DAY}&user_id={a['id']}", headers=spoof).json()
    assert data["summary"]["average_calories"] == 2200
    assert data["summary"]["last_weight_kg"] == 84


@pytest.mark.parametrize("route", [f"/daily-records/{DAY}", f"/tracking?end={DAY}"])
def test_anonymous_tracking_read_is_private(client_factory, route):
    response = client_factory().get(route)
    assert response.status_code == 401
    assert "no-store" in response.headers["cache-control"]


def test_record_mutations_require_auth_csrf_and_same_origin(client_factory, db_session):
    browser = client_factory()
    assert save(browser).status_code == 401
    register(browser, "tracking_alice")
    browser.headers.pop("X-NutriChat-Request")
    assert save(browser).status_code == 403
    browser.headers["X-NutriChat-Request"] = "1"
    denied = browser.put(f"/daily-records/{DAY}", headers={"Origin": "https://other.test"},
                         json={"revision": 0, "weight_kg": 70, "manual_calories": 1900})
    assert denied.status_code == 403
    assert db_session.query(DailyRecord).count() == 0
    accepted = browser.put(f"/daily-records/{DAY}", headers={"Origin": "http://testserver"},
                           json={"revision": 0, "weight_kg": 70, "manual_calories": 1900})
    assert accepted.status_code == 200


def test_logout_hides_records_and_login_restores_them(client_factory):
    browser = client_factory()
    register(browser, "tracking_alice")
    saved = save(browser).json()
    assert browser.post("/auth/logout").status_code == 204
    assert browser.get(f"/daily-records/{DAY}").status_code == 401
    assert browser.get(f"/tracking?end={DAY}").status_code == 401
    assert save(browser, revision=1).status_code == 401
    assert browser.post("/auth/login", json={
        "username": "tracking_alice", "password": PASSWORD,
    }).status_code == 200
    assert browser.get(f"/daily-records/{DAY}").json() == saved


@pytest.mark.parametrize("revision", [0, 2, 999])
def test_stale_revision_never_overwrites_record(client, revision):
    first = save(client).json()
    response = save(client, revision=revision, weight_kg=80)
    assert response.status_code == 409
    assert "no-store" in response.headers["cache-control"]
    assert client.get(f"/daily-records/{DAY}").json() == first


def test_nonzero_revision_cannot_create_missing_record(client, db_session):
    assert save(client, revision=1).status_code == 409
    assert db_session.query(DailyRecord).count() == 0
    assert save(client).status_code == 200


def test_two_browser_edits_conflict_and_explicit_reload_allows_retry(client_factory):
    first, second = client_factory(), client_factory()
    register(first, "tracking_alice")
    assert second.post("/auth/login", json={
        "username": "tracking_alice", "password": PASSWORD,
    }).status_code == 200
    original = save(first).json()
    assert second.get(f"/daily-records/{DAY}").json() == original
    winner = save(first, revision=1, weight_kg=71).json()
    assert save(second, revision=1, weight_kg=68).status_code == 409
    assert second.get(f"/daily-records/{DAY}").json() == winner
    retried = save(second, revision=2, weight_kg=68)
    assert retried.status_code == 200
    assert retried.json()["revision"] == 3
    assert first.get(f"/daily-records/{DAY}").json() == retried.json()


@pytest.mark.parametrize("changes", [
    {"weight_kg": 29.9}, {"weight_kg": 250.1}, {"weight_kg": "70"},
    {"weight_kg": True}, {"manual_calories": -1}, {"manual_calories": 20001},
    {"manual_calories": "2000"}, {"manual_calories": False},
    {"revision": -1}, {"revision": True}, {"revision": "1"},
    {"revision": 1.5}, {"revision": 2147483647},
])
def test_invalid_record_edit_preserves_existing_record(client, changes):
    original = save(client).json()
    response = save(client, **{"revision": 1, **changes})
    assert response.status_code == 422
    assert client.get(f"/daily-records/{DAY}").json() == original


@pytest.mark.parametrize("field", ["revision", "weight_kg", "manual_calories"])
def test_partial_put_is_rejected_instead_of_silently_clearing_other_field(client, field):
    original = save(client, manual_calories=1800).json()
    payload = {"revision": 1, "weight_kg": 71, "manual_calories": 1900}
    del payload[field]
    response = client.put(f"/daily-records/{DAY}", json=payload)
    assert response.status_code == 422
    assert client.get(f"/daily-records/{DAY}").json() == original


@pytest.mark.parametrize("field", ["user_id", "owner_id", "calories", "meal_count", "date"])
def test_record_cannot_mass_assign_owner_or_derived_fields(client, db_session, field):
    response = save(client, **{field: "private-input-must-not-be-echoed"})
    assert response.status_code == 422
    assert "private-input-must-not-be-echoed" not in response.text
    assert db_session.query(DailyRecord).count() == 0


@pytest.mark.parametrize("field", ["weight_kg", "manual_calories"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_records_return_safe_422(client, db_session, field, value):
    response = client.put(f"/daily-records/{DAY}",
                          content=json.dumps({"revision": 0, "weight_kg": 70,
                                              "manual_calories": None, field: value}),
                          headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert all(set(error) == {"loc", "msg", "type"} for error in response.json()["detail"])
    assert db_session.query(DailyRecord).count() == 0


@pytest.mark.parametrize("day", [
    "1999-12-31", "2999-01-01", "2024-2-01", "2024-02-1", "2023-02-29",
    "2024-13-01", "2024-02-30", "2024-01-01T00:00:00", "1709251200", "private-date",
])
def test_invalid_record_dates_never_create_data(client, db_session, day):
    assert client.get(f"/daily-records/{day}").status_code == 422
    assert save(client, day).status_code == 422
    assert db_session.query(DailyRecord).count() == 0


@pytest.mark.parametrize("end", ["2000-01-29", "2999-01-01", "2024-2-01", "invalid"])
def test_invalid_trend_window_is_rejected(client, end):
    response = client.get(f"/tracking?end={end}")
    assert response.status_code == 422
    assert "no-store" in response.headers["cache-control"]


@pytest.mark.parametrize(("weight", "calories"), [(30, 0), (250, 20000)])
def test_boundary_measurements_are_recorded(client, weight, calories):
    response = save(client, weight_kg=weight, manual_calories=calories)
    assert response.status_code == 200, response.text
    assert response.json()["weight_kg"] == weight
    assert response.json()["calories"] == calories


def test_confirmation_dates_meal_and_repeated_confirmation_cannot_double_count(
        client, db_session):
    owner = client.get("/auth/me").json()["id"]
    pending = meal(db_session, owner, 600, day=None, status="completed")
    assert client.get(f"/daily-records/{DAY}").json()["calories"] is None
    path = f"/analyses/{pending.id}/confirm"
    response = client.post(path, json={"revision": 1, "consumed_on": DAY})
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["consumed_on"] == DAY
    assert saved["revision"] == 2
    assert client.get(f"/analyses/{pending.id}").json()["consumed_on"] == DAY
    record = client.get(f"/daily-records/{DAY}").json()
    assert record["calories"] == 600
    assert record["meal_count"] == 1
    for revision in [1, 2]:
        assert client.post(path, json={"revision": revision,
                                      "consumed_on": "2024-03-02"}).status_code == 409
    assert client.get(f"/daily-records/{DAY}").json() == record
    assert client.get("/daily-records/2024-03-02").json()["calories"] is None


@pytest.mark.parametrize("day", [
    "1999-12-31", "2999-01-01", "2024-2-01", "2023-02-29",
    "2024-01-01T00:00:00", 1709251200, True,
])
def test_invalid_consumed_date_does_not_confirm_meal(client, db_session, day):
    owner = client.get("/auth/me").json()["id"]
    pending = meal(db_session, owner, status="completed", day=None)
    response = client.post(f"/analyses/{pending.id}/confirm",
                           json={"revision": 1, "consumed_on": day})
    assert response.status_code == 422
    db_session.refresh(pending)
    assert pending.status == "completed"
    assert pending.consumed_on is None
    assert pending.revision == 1


@pytest.mark.parametrize("day", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_confirmation_date_is_safe_validation_error(client, db_session, day):
    owner = client.get("/auth/me").json()["id"]
    pending = meal(db_session, owner, day=None, status="completed")
    response = client.post(
        f"/analyses/{pending.id}/confirm",
        content=json.dumps({"revision": 1, "consumed_on": day}),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert all(set(error) == {"loc", "msg", "type"} for error in response.json()["detail"])
    db_session.refresh(pending)
    assert pending.status == "completed"
    assert pending.consumed_on is None


@pytest.mark.parametrize("revision", [True, "1", 1.5, 2147483647])
def test_confirmation_revision_cannot_be_coerced_or_overflow(client, db_session, revision):
    owner = client.get("/auth/me").json()["id"]
    pending = meal(db_session, owner, day=None, status="completed")
    response = client.post(f"/analyses/{pending.id}/confirm",
                           json={"revision": revision, "consumed_on": DAY})
    assert response.status_code == 422
    db_session.refresh(pending)
    assert pending.status == "completed"
    assert pending.consumed_on is None
    assert pending.revision == 1


def test_hong_kong_midnight_sets_defaults_and_rejects_tomorrow(client, db_session, monkeypatch):
    from services.common import tracking

    class FixedDatetime:
        @classmethod
        def now(cls, tz):
            # UTC is still February 29; Hong Kong has just entered March 1.
            instant = datetime(2024, 2, 29, 16, 0, tzinfo=timezone.utc)
            return instant.astimezone(tz)

    monkeypatch.setattr(tracking, "datetime", FixedDatetime)
    assert tracking.hong_kong_today() == date(2024, 3, 1)
    response = client.get("/tracking")
    assert response.status_code == 200
    data = response.json()
    assert data["today"] == data["end_date"] == "2024-03-01"
    assert data["start_date"] == "2024-02-01"
    assert save(client, "2024-03-01").status_code == 200
    assert save(client, "2024-03-02").status_code == 422
    assert client.get("/tracking?end=2024-03-02").status_code == 422
    owner = client.get("/auth/me").json()["id"]
    pending = meal(db_session, owner, day=None, status="completed")
    confirmed = client.post(f"/analyses/{pending.id}/confirm", json={"revision": 1})
    assert confirmed.status_code == 200
    assert confirmed.json()["consumed_on"] == "2024-03-01"
    assert client.get("/daily-records/2024-03-01").json()["meal_count"] == 1
    assert client.get("/daily-records/2024-02-29").json()["meal_count"] == 0


def test_tracking_does_not_call_ai_or_queue_jobs(client, db_session, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Recording history must not send personal data to Qwen")

    monkeypatch.setattr("services.ai.app.qwen.analyze_with_qwen", forbidden)
    monkeypatch.setattr("httpx.post", forbidden)
    assert save(client, manual_calories=2000).status_code == 200
    assert client.get(f"/daily-records/{DAY}").status_code == 200
    assert client.get(f"/tracking?end={DAY}").status_code == 200
    assert db_session.query(Job).count() == 0
