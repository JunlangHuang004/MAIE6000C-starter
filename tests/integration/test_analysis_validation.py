"""Malformed revisions must be rejected without queuing work or changing a meal."""
import json

import pytest

from services.common.models import Analysis, Job


@pytest.mark.parametrize("method,suffix,payload", [
    ("PATCH", "", {"food_text": "100g egg"}),
    ("POST", "/mode", {"mode": "basic"}),
    ("POST", "/reply", {"message": "100g egg"}),
    ("POST", "/confirm", {}),
    ("POST", "/ingredients", {
        "item_index": 0, "name": "Synthetic egg recipe", "basis": "consumed",
        "accepted": True, "ingredients": [{"food_id": "egg", "grams": 100}],
    }),
])
@pytest.mark.parametrize("revision", [
    True, "1", 1.0, 1.5, 0, -1, 2_147_483_647, 10 ** 100,
    float("nan"), float("inf"), -float("inf"),
])
def test_invalid_analysis_revision_is_safe_422_without_mutation(
    client, db_session, method, suffix, payload, revision,
):
    owner = client.get("/auth/me").json()["id"]
    meal = Analysis(
        user_id=owner, food_text="100g egg", status="completed", revision=1,
        calories=155, protein_g=13, carbs_g=1.1, fat_g=11,
    )
    db_session.add(meal)
    db_session.commit()
    path = f"/analyses/{meal.id}"
    original = client.get(path).json()
    jobs_before = db_session.query(Job).count()

    response = client.request(
        method, path + suffix, content=json.dumps({**payload, "revision": revision}),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    assert errors
    assert all(error["loc"] == ["body", "revision"] for error in errors)
    assert all(set(error) == {"loc", "msg", "type"} for error in errors)
    assert client.get(path).json() == original
    assert db_session.query(Job).count() == jobs_before
