import pytest
from fastapi.testclient import TestClient

from services.ai.app import main as ai_main
from services.common.config import Settings
from services.common.schemas import NutritionAnalysisResponse


def test_qwen_route_dispatches_and_preserves_interpretation(monkeypatch):
    monkeypatch.setattr(ai_main, 'get_settings', lambda: Settings(
        _env_file=None, nutrition_provider='qwen',
    ))

    def extract(text, settings, history=None, mode='advanced'):
        assert text == '100克鸡蛋'
        assert settings.nutrition_provider == 'qwen'
        return NutritionAnalysisResponse(
            calories=155, protein_g=13, carbs_g=1.1, fat_g=11,
            interpreted_food_text='100g egg',
        )

    monkeypatch.setattr(ai_main, 'analyze_with_qwen', extract)
    with TestClient(ai_main.app) as client:
        response = client.post('/analyze-nutrition', json={
            'analysis_id': 'test-meal', 'food_text': '100克鸡蛋',
        })
    assert response.status_code == 200
    assert response.json()['interpreted_food_text'] == '100g egg'
    assert response.json()['calories'] == 155


@pytest.mark.parametrize('error,status', [
    (ValueError('Meal needs correction'), 422),
    (RuntimeError('Qwen request failed or timed out'), 502),
])
def test_qwen_route_does_not_return_estimate_on_failure(monkeypatch, error, status):
    monkeypatch.setattr(ai_main, 'get_settings', lambda: Settings(
        _env_file=None, nutrition_provider='qwen',
    ))

    def fail(*args):
        raise error

    monkeypatch.setattr(ai_main, 'analyze_with_qwen', fail)
    with TestClient(ai_main.app) as client:
        response = client.post('/analyze-nutrition', json={
            'analysis_id': 'test-meal', 'food_text': '100克鸡蛋',
        })
    assert response.status_code == status
    assert 'calories' not in response.json()


def test_qwen_mode_queues_chinese_input(client, monkeypatch):
    monkeypatch.setattr('services.common.config.get_settings', lambda: Settings(
        _env_file=None, nutrition_provider='qwen',
    ))
    response = client.post('/analyses', json={'food_text': '100克鸡蛋'})
    assert response.status_code == 201
    assert response.json()['analysis']['status'] == 'queued'
    assert response.json()['analysis']['calories'] is None
