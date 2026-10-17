"""Week 6 lifecycle contracts; SQLite does not prove PostgreSQL lock concurrency."""

import httpx
import pytest

from services.common.db import make_session_factory
from services.common.models import Analysis, Job
from services.worker.app import main as worker


@pytest.fixture()
def worker_factory(db_session, monkeypatch):
    factory = make_session_factory(db_session.get_bind())
    monkeypatch.setattr(worker, "get_session_factory", lambda: factory)
    return factory


def test_claim_persists_attempt_and_does_not_reclaim_interrupted_job(client, worker_factory):
    created = client.post("/analyses", json={"food_text": "100g egg"}).json()
    job_id = created["job"]["id"]
    assert created["job"]["attempts"] == 0
    with worker_factory() as db:
        claimed = worker.claim_next_pending_job(db)
        assert claimed.id == job_id

    # A fresh session represents another poll/restart after the first claim committed.
    with worker_factory() as db:
        stored = db.get(Job, job_id)
        assert stored.status == "claimed"
        assert stored.attempts == 1
        assert stored.claimed_at is not None
        assert stored.completed_at is None
        assert worker.claim_next_pending_job(db) is None
        assert db.get(Analysis, created["analysis"]["id"]).status == "queued"


@pytest.mark.parametrize("outcome", ["success", "timeout", "http_error", "malformed"])
def test_worker_loop_persists_processor_outcome(
    client, db_session, worker_factory, monkeypatch, outcome,
):
    created = client.post("/analyses", json={"food_text": "100g egg"}).json()
    calls = []

    def processor(url, *, json, timeout):
        calls.append(json)
        assert url.endswith("/analyze-nutrition")
        assert json["analysis_id"] == created["analysis"]["id"]
        assert json["food_text"] == "100g egg"
        assert json["mode"] == "advanced"
        assert json["conversation"] == [{"role": "user", "content": "100g egg"}]
        assert json["draft"] == []
        assert 0 < timeout == worker.settings.worker_request_timeout_seconds
        if outcome == "timeout":
            raise httpx.ReadTimeout("Synthetic processor timeout")
        result = {"calories": 155, "protein_g": 13, "carbs_g": 1.1, "fat_g": 11}
        if outcome == "malformed":
            result = {"calories": 155}  # Missing required nutrient totals.
        return httpx.Response(
            503 if outcome == "http_error" else 200,
            json=result, request=httpx.Request("POST", url),
        )

    def stop_at_next_poll(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(worker.httpx, "post", processor)
    monkeypatch.setattr(worker.time, "sleep", stop_at_next_poll)
    with pytest.raises(KeyboardInterrupt):
        worker.run_worker()

    assert len(calls) == 1  # The policy is one attempt; there is no automatic retry.
    db_session.expire_all()
    result = client.get("/analyses/" + created["analysis"]["id"]).json()
    job = client.get(f"/jobs/{created['job']['id']}").json()
    expected = "completed" if outcome == "success" else "failed"
    assert result["status"] == job["status"] == expected
    assert job["attempts"] == 1
    assert job["claimed_at"] and job["completed_at"]
    with worker_factory() as db:
        assert db.get(Job, job["id"]).status == expected
        assert db.get(Analysis, result["id"]).status == expected
        assert worker.claim_next_pending_job(db) is None
    if outcome == "success":
        assert result["calories"] == 155
        assert result["protein_g"] == 13
        assert result["carbs_g"] == 1.1
        assert result["fat_g"] == 11
        assert result["error_message"] is None
        assert job["error"] is None
    else:
        assert all(result[key] is None for key in ("calories", "protein_g", "carbs_g", "fat_g"))
        assert result["error_message"]
        assert "Synthetic" not in result["error_message"]
        assert job["error"] and len(job["error"]) <= 1000


def test_repeated_post_creates_separate_records_without_idempotency(client, db_session):
    first = client.post("/analyses", json={"food_text": "100g egg"})
    second = client.post("/analyses", json={"food_text": "100g egg"})
    assert first.status_code == second.status_code == 201
    assert first.json()["analysis"]["id"] != second.json()["analysis"]["id"]
    assert first.json()["job"]["id"] != second.json()["job"]["id"]
    assert db_session.query(Analysis).count() == 2
    assert db_session.query(Job).count() == 2
