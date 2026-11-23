"""Persist mixed-definition nutrition and preserve previously saved recipe totals."""
from copy import deepcopy

import httpx
import pytest

from services.common import meal_engine
from services.common.config import Settings
from services.common.db import make_session_factory
from services.common.meal_engine import ExtractedItem, catalogue, evaluate_mode
from services.common.models import Analysis
from services.worker.app import main as worker


@pytest.fixture()
def reference_worker(db_session, monkeypatch):
    settings = Settings(_env_file=None, nutrition_provider='qwen', llm_provider='qwen')
    monkeypatch.setattr('services.common.config.get_settings', lambda: settings)
    monkeypatch.setattr('services.api.app.main.get_settings', lambda: settings)
    monkeypatch.setattr(worker, 'get_session_factory',
                        lambda: make_session_factory(db_session.get_bind()))
    initial = [
        ExtractedItem(food_id='dish_266', name='菠萝咕咾肉', grams=100,
                      weight_basis='cooked').model_dump(),
        ExtractedItem(food_id='rice', name='白米饭', grams=100).model_dump(),
    ]

    def respond(url, **kwargs):
        payload = kwargs['json']
        result = evaluate_mode(payload.get('draft') or initial, payload['mode'])
        return httpx.Response(200, request=httpx.Request('POST', url), json=result)

    monkeypatch.setattr(worker.httpx, 'post', respond)
    return initial


def finish(client, db_session, response):
    assert response.status_code in (200, 201), response.text
    data = response.json()
    worker.process_nutrition_job(data['job']['id'])
    db_session.expire_all()
    return client.get('/analyses/' + data['analysis']['id']).json()


def test_mixed_meal_worker_confirm_reload_preserves_source_and_carbohydrate_definitions(
        client, db_session, monkeypatch, reference_worker):
    meal = finish(client, db_session, client.post('/analyses', json={
        'food_text': '菠萝咕咾肉100克，白米饭100克', 'mode': 'basic',
    }))
    assert meal['status'] == 'completed'
    assert meal['calories'] == 370 and meal['carbs_g'] is None
    assert meal['protein_g'] is not None and meal['fat_g'] is not None
    assert meal['carbohydrate_summary']['basis'] == 'mixed'
    assert meal['details'][0]['calculation_basis'] == 'measured_reference'
    assert meal['details'][0]['sources'][0]['url'].startswith('https://www.cfs.gov.hk/')
    saved = deepcopy(meal)
    path = '/analyses/' + meal['id']
    confirmed = client.post(path + '/confirm', json={'revision': meal['revision']})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()['status'] == 'confirmed'

    changed = deepcopy(catalogue())
    food = next(food for food in changed['foods'] if food['id'] == 'dish_266')
    food['measured_reference']['nutrients']['calories'] = 999
    food['measured_reference']['source']['name'] = 'Future reference'
    monkeypatch.setattr(meal_engine, 'catalogue', lambda: changed)
    reloaded = client.get(path).json()
    for key in ('calories', 'protein_g', 'fat_g', 'carbs_g', 'details', 'carbohydrate_summary'):
        assert reloaded[key] == saved[key]
    assert client.post(path + '/mode', json={
        'revision': reloaded['revision'], 'mode': 'advanced'}).status_code == 409


def test_advanced_selection_worker_uses_measured_or_true_ingredient_path(
        client, db_session, reference_worker):
    meal = finish(client, db_session, client.post('/analyses', json={
        'food_text': '菠萝咕咾肉100克，白米饭100克', 'mode': 'advanced',
    }))
    assert meal['status'] == 'needs_input'
    assert '0.calculation_basis' in {q['key'] for q in meal['questions']}
    path = '/analyses/' + meal['id']
    meal = finish(client, db_session, client.post(path + '/reply', json={
        'revision': meal['revision'], 'answers': {
            '0.calculation_basis': 'measured_reference',
            '1.weight_basis': 'cooked', '1.preparation': 'as_served',
        },
    }))
    assert meal['status'] == 'completed' and meal['calories'] == 370
    assert meal['carbs_g'] is None
    assert meal['draft'][0]['calculation_basis'] == 'measured_reference'


def test_historical_recipe_snapshot_is_not_recalculated_by_new_reference(
        client, db_session, reference_worker):
    created = client.post('/analyses', json={
        'food_text': '菠萝咕咾肉100克', 'mode': 'basic',
    }).json()['analysis']
    draft = [deepcopy(reference_worker[0])]
    draft[0]['calculation_basis'] = 'ingredient_recipe'
    historical = evaluate_mode(draft, 'basic')
    historical['draft'][0].pop('calculation_basis')
    for detail in historical['details']:
        for key in ('calculation_basis', 'calculation_evidence', 'carbohydrate_basis'):
            detail.pop(key)
    row = db_session.get(Analysis, created['id'])
    row.status = 'confirmed'
    for key in ('draft', 'details', 'calories', 'protein_g', 'fat_g', 'carbs_g'):
        setattr(row, key, historical[key])
    db_session.commit()
    reloaded = client.get('/analyses/' + row.id).json()
    assert reloaded['calories'] == 174.2
    assert reloaded['calories'] != 240
    assert reloaded['details'] == historical['details']
    assert reloaded['carbs_g'] == historical['carbs_g']
    assert reloaded['carbohydrate_summary']['basis'] == 'total_by_difference'
