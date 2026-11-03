"""Merged accounts + structured recipes + diary integration and ownership boundaries.

The calculator/worker are real; extraction is a controlled fixture. No provider
request or private credentials are used by these checks.
"""
import json
from copy import deepcopy

import httpx
import pytest
from sqlalchemy import func, select

from services.api.app import main as api
from services.common.db import make_session_factory
from services.common.meal_engine import ExtractedItem, evaluate_mode
from services.common.models import Analysis, Job
from services.worker.app import main as worker


DAY = '2024-03-01'


def recipe_payload(**changes):
    return {
        'revision': 1, 'item_index': 0, 'name': 'Reviewed chicken bowl',
        'basis': 'batch', 'accepted': True,
        'ingredients': [
            {'food_id': 'chicken', 'grams': 300},
            {'food_id': 'oil', 'grams': 10},
            {'food_id': 'soy_sauce', 'grams': 20},
        ],
        'batch_yield_g': 600, 'consumed_g': 150, **changes,
    }


def seed_unknown(db_session, owner):
    draft = [
        ExtractedItem(name='火星豉油鸡', source_text='火星豉油鸡', grams=200).model_dump(),
        ExtractedItem(name='米饭', source_text='米饭', food_id='rice', grams=100,
                      weight_basis='cooked', preparation='as_served').model_dump(),
    ]
    row = Analysis(
        user_id=owner, food_text='火星豉油鸡配米饭', mode='basic', status='needs_input',
        conversation=[{'role': 'user', 'content': '火星豉油鸡配米饭'}],
        **evaluate_mode(draft, 'basic'),
    )
    db_session.add(row)
    db_session.commit()
    return row


@pytest.mark.parametrize('actor', ['anonymous', 'stranger', 'legacy'])
def test_recipe_endpoint_cannot_mutate_another_or_ownerless_meal(
        client, client_factory, db_session, actor):
    owner_id = client.get('/auth/me').json()['id']
    row = seed_unknown(db_session, None if actor == 'legacy' else owner_id)
    original = deepcopy(row.draft)
    outsider = client_factory()
    if actor != 'anonymous':
        registered = outsider.post('/auth/register', json={
            'username': 'recipe_stranger', 'password': 'Synthetic-recipe-password-42',
        })
        assert registered.status_code == 201
    response = outsider.post(f'/analyses/{row.id}/ingredients', json=recipe_payload())
    assert response.status_code == (401 if actor == 'anonymous' else 404)
    db_session.refresh(row)
    assert row.revision == 1 and row.status == 'needs_input'
    assert row.draft == original
    assert db_session.scalar(select(func.count(Job.id))) == 0


@pytest.mark.parametrize('headers', [
    {'X-NutriChat-Request': ''},
    {'Origin': 'https://foreign.example'},
])
def test_recipe_mutation_requires_same_origin_request_guard(client, db_session, headers):
    row = seed_unknown(db_session, client.get('/auth/me').json()['id'])
    response = client.post(f'/analyses/{row.id}/ingredients',
                           json=recipe_payload(), headers=headers)
    assert response.status_code == 403
    assert db_session.scalar(select(func.count(Job.id))) == 0
    db_session.refresh(row)
    assert row.revision == 1 and row.status == 'needs_input'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf')])
def test_non_finite_recipe_quantity_returns_validation_error_without_mutation(
        client, db_session, value):
    row = seed_unknown(db_session, client.get('/auth/me').json()['id'])
    payload = recipe_payload(ingredients=[{'food_id': 'chicken', 'grams': value}])
    response = client.post(
        f'/analyses/{row.id}/ingredients', content=json.dumps(payload),
        headers={'Content-Type': 'application/json'},
    )
    assert response.status_code == 422
    assert 'input' not in str(response.json())
    assert db_session.scalar(select(func.count(Job.id))) == 0
    db_session.refresh(row)
    assert row.revision == 1 and row.status == 'needs_input'


def test_custom_recipe_confirmation_flows_into_private_daily_and_30_day_records(
        client, client_factory, db_session, monkeypatch):
    owner_id = client.get('/auth/me').json()['id']
    row = seed_unknown(db_session, owner_id)
    path = '/analyses/' + row.id
    monkeypatch.setattr(worker, 'get_session_factory',
                        lambda: make_session_factory(db_session.get_bind()))

    def respond(url, **kwargs):
        request = kwargs['json']
        assert request['draft'][0]['custom_recipe']['accepted'] is True
        return httpx.Response(200, request=httpx.Request('POST', url),
                              json=evaluate_mode(request['draft'], request['mode']))

    monkeypatch.setattr(worker.httpx, 'post', respond)
    queued = client.post(path + '/ingredients', json=recipe_payload())
    assert queued.status_code == 200, queued.text
    worker.process_nutrition_job(queued.json()['job']['id'])
    db_session.expire_all()
    result = client.get(path).json()
    assert result['status'] == 'completed' and result['calories'] == 244.8
    # The unconfirmed estimate is not intake, even though it has nutrients.
    assert client.get(f'/daily-records/{DAY}').json()['calories'] is None
    confirmed = client.post(path + '/confirm', json={
        'revision': result['revision'], 'consumed_on': DAY,
    })
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()['consumed_on'] == DAY
    assert client.get(path).json() == confirmed.json()
    assert client.post(path + '/ingredients', json=recipe_payload(
        revision=confirmed.json()['revision'])).status_code == 409
    daily = client.put(f'/daily-records/{DAY}', json={
        'revision': 0, 'weight_kg': 72.5, 'manual_calories': None,
    }).json()
    assert daily['calories'] == daily['meal_calories'] == 244.8
    assert daily['meal_count'] == 1 and daily['calorie_source'] == 'meals'
    trend = client.get(f'/tracking?end={DAY}').json()
    assert len(trend['days']) == 30 and trend['days'][-1] == daily
    assert trend['summary']['average_calories'] == 244.8
    assert trend['summary']['weight_entries'] == 1
    stranger = client_factory()
    assert stranger.post('/auth/register', json={
        'username': 'diary_stranger', 'password': 'Synthetic-recipe-password-42',
    }).status_code == 201
    assert stranger.get(path).status_code == 404
    assert stranger.get(f'/jobs/{queued.json()["job"]["id"]}').status_code == 404
    assert stranger.get('/analyses').json() == []
    private_trend = stranger.get(f'/tracking?end={DAY}').json()
    assert all(day['calories'] is None and day['weight_kg'] is None
               for day in private_trend['days'])


@pytest.mark.parametrize('selector,reported', [
    ('qwen', 'qwen'), ('hkust', 'hkust'), ('ollama', 'ollama'), ('heuristic', 'demo'),
])
def test_public_catalogue_reports_effective_provider_and_expanded_data(
        client, auth_settings, monkeypatch, selector, reported):
    monkeypatch.setattr(auth_settings, 'nutrition_provider', 'demo')
    monkeypatch.setattr(auth_settings, 'llm_provider', selector)
    monkeypatch.setattr(api, 'get_settings', lambda: auth_settings)
    response = client.get('/foods')
    assert response.status_code == 200
    payload = response.json()
    assert payload['provider'] == reported
    foods = payload['catalogue']['foods']
    assert len(foods) == 550
    assert sum(food['kind'] == 'recipe' for food in foods) == 350
    assert next(food for food in foods if food['id'] == 'dish_251')['name'] == '豉油鸡'


def test_offline_conversation_is_rejected_and_full_description_correction_is_queued(
        client, db_session, auth_settings, monkeypatch):
    monkeypatch.setattr(auth_settings, 'llm_provider', 'heuristic')
    monkeypatch.setattr(api, 'get_settings', lambda: auth_settings)
    created = client.post('/analyses', json={'food_text': '100g egg'}).json()
    row = db_session.get(Analysis, created['analysis']['id'])
    row.status = 'completed'
    row.calories, row.protein_g, row.fat_g, row.carbs_g = 155, 13, 11, 1.1
    db_session.commit()
    path = '/analyses/' + row.id
    before = client.get(path).json()
    jobs_before = db_session.scalar(select(func.count(Job.id)))
    response = client.post(path + '/reply', json={
        'revision': row.revision, 'message': 'Actually I ate 200g egg',
    })
    assert response.status_code == 422
    assert 'full meal description' in response.json()['detail']
    assert client.get(path).json() == before
    assert db_session.scalar(select(func.count(Job.id))) == jobs_before
    changed = client.patch(path, json={'revision': row.revision, 'food_text': '200g egg'})
    assert changed.status_code == 200
    assert changed.json()['analysis']['status'] == 'queued'
    assert changed.json()['analysis']['food_text'] == '200g egg'
    assert changed.json()['analysis']['calories'] is None
    assert db_session.scalar(select(func.count(Job.id))) == jobs_before + 1
