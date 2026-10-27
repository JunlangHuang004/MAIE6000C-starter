from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.smoke


def test_smoke_end_to_end_case_flow(smoke_client):
    create_response = smoke_client.post(
        "/cases",
        json={
            "title": "Production outage alert",
            "description": "Several users report the service is down and requests are failing.",
        },
        timeout=10,
    )
    assert create_response.status_code == 201

    case_id = create_response.json()["case"]["id"]

    deadline = time.time() + 30
    last_payload = None

    while time.time() < deadline:
        poll = smoke_client.get(f"/cases/{case_id}", timeout=10)
        assert poll.status_code == 200
        last_payload = poll.json()

        if last_payload["status"] == "triaged":
            break

        time.sleep(1)

    assert last_payload is not None
    assert last_payload["status"] == "triaged"
    assert last_payload["ai_label"] in {
        "access",
        "incident",
        "billing",
        "maintenance",
        "general",
    }
