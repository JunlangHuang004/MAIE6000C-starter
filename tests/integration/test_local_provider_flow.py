"""Exercise NutriChat's persisted flow while replacing only the model HTTP boundary."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from services.ai.app import main as ai_main
from services.api.app import main as api_main
from services.common.config import Settings
from services.common.db import make_session_factory
from services.common.meal_engine import catalogue
from services.worker.app import main as worker


@pytest.fixture(autouse=True)
def clear_provider_environment(monkeypatch):
    for name in ("LLM_PROVIDER", "LLM_API_KEY", "DASHSCOPE_API_KEY", "QWEN_BASE_URL"):
        monkeypatch.delenv(name, raising=False)


def settings_for(provider):
    return Settings(
        _env_file=None, nutrition_provider="demo", llm_provider=provider,
        llm_base_url=("http://127.0.0.1:11434" if provider == "ollama"
                      else "https://hkust.example.test/v1"),
        llm_api_key="synthetic-test-key" if provider == "hkust" else "",
        auth_cookie_secure=False,
    )


def install_settings(monkeypatch, settings):
    monkeypatch.setattr(ai_main, "get_settings", lambda: settings)
    monkeypatch.setattr(api_main, "get_settings", lambda: settings)
    monkeypatch.setattr("services.common.config.get_settings", lambda: settings)


@pytest.mark.parametrize("provider", ["hkust", "ollama"])
def test_provider_meal_clarification_confirm_and_reload(
    client, db_session, monkeypatch, provider,
):
    settings = settings_for(provider)
    install_settings(monkeypatch, settings)
    monkeypatch.setattr(
        worker, "get_session_factory", lambda: make_session_factory(db_session.get_bind()),
    )
    model_calls = []
    with TestClient(ai_main.app) as ai_client:
        def route_request(url, **kwargs):
            if url.endswith("/analyze-nutrition"):
                response = ai_client.post("/analyze-nutrition", json=kwargs["json"])
                return httpx.Response(
                    response.status_code, json=response.json(),
                    request=httpx.Request("POST", url),
                )
            model_calls.append((url, kwargs))
            content = json.dumps({"items": [{
                "food_id": "egg", "name": "水煮鸡蛋", "grams": None,
                "preparation": "boiled", "weight_basis": "cooked",
            }]})
            if provider == "ollama":
                result = {"message": {"content": content}, "done": True, "done_reason": "stop"}
            else:
                result = {"choices": [{
                    "finish_reason": "stop", "message": {"content": content},
                }]}
            return httpx.Response(200, json=result, request=httpx.Request("POST", url))

        monkeypatch.setattr(httpx, "post", route_request)
        assert client.get("/foods").json()["provider"] == provider
        created = client.post("/analyses", json={
            "food_text": "去壳水煮鸡蛋，熟重", "mode": "advanced",
        })
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["analysis"]["status"] == "queued"
        worker.process_nutrition_job(body["job"]["id"])
        db_session.expire_all()
        path = "/analyses/" + body["analysis"]["id"]
        meal = client.get(path).json()
        assert meal["status"] == "needs_input"
        assert meal["calories"] is None
        assert "0.grams" in {question["key"] for question in meal["questions"]}
        assert client.post(path + "/confirm", json={
            "revision": meal["revision"],
        }).status_code == 409

        corrected = client.post(path + "/reply", json={
            "revision": meal["revision"], "answers": {"0.grams": 125},
        })
        assert corrected.status_code == 200, corrected.text
        worker.process_nutrition_job(corrected.json()["job"]["id"])
        db_session.expire_all()
        complete = client.get(path).json()
        assert complete["status"] == "completed"
        assert complete["questions"] == []
        egg = next(food for food in catalogue()["foods"] if food["id"] == "egg")
        assert complete["calories"] == round(egg["nutrients"]["calories"] * 1.25, 1)
        assert complete["details"][0]["grams"] == 125
        assert complete["details"][0]["sources"]
        # Structured answers use arithmetic, without another model call.
        assert len(model_calls) == 1

        saved = client.post(path + "/confirm", json={"revision": complete["revision"]})
        assert saved.status_code == 200, saved.text
        db_session.expire_all()
        reloaded = client.get(path).json()
        assert reloaded["status"] == "confirmed"
        assert reloaded["calories"] == complete["calories"]
        assert len(model_calls) == 1


@pytest.mark.parametrize("provider", ["hkust", "ollama"])
def test_provider_failure_returns_502_without_estimate_or_private_details(monkeypatch, provider):
    install_settings(monkeypatch, settings_for(provider))

    def reject(url, **kwargs):
        return httpx.Response(
            401, json={"error": "SYNTHETIC_PRIVATE_DETAIL synthetic-test-key"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", reject)
    with TestClient(ai_main.app) as client:
        response = client.post("/analyze-nutrition", json={
            "analysis_id": "synthetic-failure", "food_text": "100克水煮鸡蛋",
        })
    assert response.status_code == 502
    assert "calories" not in response.json()
    assert "synthetic-test-key" not in response.text
    assert "SYNTHETIC_PRIVATE_DETAIL" not in response.text


def test_heuristic_course_mode_runs_without_network_and_keeps_demo_validation(client, monkeypatch):
    settings = Settings(
        _env_file=None, nutrition_provider="qwen", llm_provider="heuristic",
        dashscope_api_key="", qwen_base_url="", llm_api_key="",
    )
    install_settings(monkeypatch, settings)

    def forbidden(*args, **kwargs):
        pytest.fail("Heuristic mode must not contact Qwen, HKUST or Ollama")

    monkeypatch.setattr(httpx, "post", forbidden)
    with TestClient(ai_main.app) as ai_client:
        response = ai_client.post("/analyze-nutrition", json={
            "analysis_id": "synthetic-heuristic", "food_text": "100g egg",
        })
    assert response.status_code == 200
    assert response.json()["calories"] == 155
    assert client.get("/foods").json()["provider"] == "demo"
    assert client.post("/analyses", json={"food_text": "100g egg"}).status_code == 201
    assert client.post("/analyses", json={"food_text": "unsupported food"}).status_code == 422
