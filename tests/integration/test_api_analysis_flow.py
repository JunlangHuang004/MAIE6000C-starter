from __future__ import annotations

from services.common.db import make_session_factory
from services.worker.app import main as worker_main


def test_create_and_read_analysis_and_job(client):
    create_response = client.post(
        "/analyses",
        json={"food_text": "200g chicken breast and 230g white rice"},
    )
    assert create_response.status_code == 201

    payload = create_response.json()
    analysis_id = payload["analysis"]["id"]

    assert payload["analysis"]["food_text"] == "200g chicken breast and 230g white rice"
    assert payload["analysis"]["status"] == "queued"
    assert payload["analysis"]["calories"] is None
    assert payload["analysis"]["protein_g"] is None
    assert payload["analysis"]["carbs_g"] is None
    assert payload["analysis"]["fat_g"] is None
    assert payload["job"]["analysis_id"] == analysis_id
    assert payload["job"]["case_id"] is None
    assert payload["job"]["status"] == "pending"
    assert payload["job"]["job_type"] == "analyze_nutrition"

    read_response = client.get(f"/analyses/{analysis_id}")
    assert read_response.status_code == 200
    assert read_response.json() == payload["analysis"]


def test_create_analysis_validates_food_text_length(client):
    too_short = client.post("/analyses", json={"food_text": "ab"})
    whitespace_only = client.post("/analyses", json={"food_text": "   "})
    too_long = client.post("/analyses", json={"food_text": "a" * 2001})

    assert too_short.status_code == 422
    assert whitespace_only.status_code == 422
    assert too_long.status_code == 422


def test_read_missing_analysis_returns_404(client):
    response = client.get("/analyses/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json() == {"detail": "Analysis not found"}


def test_worker_persists_nutrition_result(client, db_session, monkeypatch):
    create_response = client.post(
        "/analyses",
        json={"food_text": "200g chicken breast and 230g white rice"},
    )
    payload = create_response.json()
    analysis_id = payload["analysis"]["id"]
    job_id = payload["job"]["id"]

    worker_session_factory = make_session_factory(db_session.get_bind())
    monkeypatch.setattr(worker_main, "get_session_factory", lambda: worker_session_factory)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "calories": 629.0,
                "protein_g": 68.2,
                "carbs_g": 64.4,
                "fat_g": 7.9,
            }

    monkeypatch.setattr(worker_main.httpx, "post", lambda *args, **kwargs: FakeResponse())

    with worker_session_factory() as worker_db:
        claimed_job = worker_main.claim_next_pending_job(worker_db)
    assert claimed_job is not None
    assert claimed_job.id == job_id

    worker_main.process_job(job_id)
    db_session.expire_all()

    read_response = client.get(f"/analyses/{analysis_id}")
    assert read_response.status_code == 200
    assert read_response.json()["status"] == "completed"
    assert read_response.json()["calories"] == 629.0
    assert read_response.json()["protein_g"] == 68.2
    assert read_response.json()["carbs_g"] == 64.4
    assert read_response.json()["fat_g"] == 7.9

    job_response = client.get(f"/jobs/{job_id}")
    assert job_response.json()["status"] == "completed"
