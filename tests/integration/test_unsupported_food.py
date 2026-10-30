"""Persisted unsupported-food behavior with a controlled internal AI boundary.

Provider name/ID grounding is tested separately; these checks exercise the API,
worker, saved draft, mode changes, user correction and confirmation lifecycle.
"""

import httpx
import pytest

from services.common.config import Settings
from services.common.db import make_session_factory
from services.common.meal_engine import ExtractedItem, evaluate_mode
from services.common.models import Analysis
from services.worker.app import main as worker


NUTRIENTS = ('calories', 'protein_g', 'fat_g', 'carbs_g')
CORRECTION = '改成200克番茄炒蛋熟重'


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
def test_unsupported_meal_stays_blocked_until_explicit_correction(
        client, db_session, monkeypatch, mode):
    monkeypatch.setattr('services.common.config.get_settings', lambda: Settings(
        _env_file=None, nutrition_provider='qwen'))
    monkeypatch.setattr(worker, 'get_session_factory',
                        lambda: make_session_factory(db_session.get_bind()))
    unknown = [
        ExtractedItem(name='豉油鸡', source_text='豉油鸡', grams=200).model_dump(),
        ExtractedItem(name='米饭', source_text='米饭', food_id='rice', grams=100,
                      weight_basis='cooked', preparation='boiled').model_dump(),
    ]
    corrected = [ExtractedItem(
        name='番茄炒蛋', source_text='番茄炒蛋', food_id='dish_001', grams=200,
        weight_basis='cooked', preparation='stir_fried').model_dump()]

    def respond(url, **kwargs):
        payload = kwargs['json']
        if payload['draft']:
            draft = payload['draft']
        elif any(entry['role'] == 'user' and entry['content'] == CORRECTION
                 for entry in payload['conversation']):
            draft = corrected
        else:
            draft = unknown
        return httpx.Response(200, request=httpx.Request('POST', url),
                              json=evaluate_mode(draft, payload['mode']))

    monkeypatch.setattr(worker.httpx, 'post', respond)

    def run_job(response):
        assert response.status_code in (200, 201), response.text
        data = response.json()
        assert data['analysis']['status'] == 'queued'
        assert all(data['analysis'][key] is None for key in NUTRIENTS)
        worker.process_nutrition_job(data['job']['id'])
        db_session.expire_all()
        return client.get('/analyses/' + data['analysis']['id']).json()

    meal = run_job(client.post('/analyses', json={
        'food_text':'200克豉油鸡和100克米饭熟重', 'mode':mode}))
    path = '/analyses/' + meal['id']

    def assert_blocked(state):
        assert state['status'] == 'needs_input'
        assert all(state[key] is None for key in NUTRIENTS)
        assert state['details'] == []
        assert state['interpreted_food_text'] is None
        assert state['draft'][0]['name'] == '豉油鸡'
        assert state['draft'][0]['food_id'] is None
        assert state['draft'][1]['food_id'] == 'rice'
        question = next(q for q in state['questions'] if q['key'] == '0.food_id')
        assert question['kind'] == 'unsupported'
        assert '数据库未找到' in question['label']
        assert 'options' not in question
        assert '豉油鸡' in state['conversation'][-1]['content']
        assert client.get(path).json() == state
        stored = db_session.get(Analysis, state['id'])
        assert stored.status == 'needs_input'
        assert all(getattr(stored, key) is None for key in NUTRIENTS)
        assert stored.confirmed_at is None
        assert client.post(path + '/confirm', json={
            'revision':state['revision']}).status_code == 409
        forged = client.post(path + '/reply', json={
            'revision':state['revision'], 'answers':{'0.food_id':'dish_010'}})
        assert forged.status_code == 422
        assert '没有对应的食物记录' in forged.json()['detail']
        assert client.get(path).json() == state

    assert_blocked(meal)
    # Neither Basic defaults nor a return to Advanced can replace the unknown food.
    for next_mode in ('advanced' if mode == 'basic' else 'basic', mode):
        meal = run_job(client.post(path + '/mode', json={
            'revision':meal['revision'], 'mode':next_mode}))
        assert meal['mode'] == next_mode
        assert_blocked(meal)

    meal = run_job(client.post(path + '/reply', json={
        'revision':meal['revision'], 'message':CORRECTION}))
    assert meal['draft'][0]['food_id'] == 'dish_001'
    assert all(q['kind'] != 'unsupported' for q in meal['questions'])
    if mode == 'advanced':
        assert meal['status'] == 'needs_input'
        recipe = next(q['recipe'] for q in meal['questions'] if q['kind'] == 'recipe')
        meal = run_job(client.post(path + '/reply', json={
            'revision':meal['revision'], 'answers':{'0.recipe':recipe}}))
    assert meal['status'] == 'completed'
    assert meal['calories'] > 0
    assert [detail['food_id'] for detail in meal['details']] == ['dish_001']
    confirmed = client.post(path + '/confirm', json={'revision':meal['revision']})
    assert confirmed.status_code == 200
    assert confirmed.json()['status'] == 'confirmed'
    assert confirmed.json()['confirmed_at']
    assert client.get(path).json() == confirmed.json()
    db_session.expire_all()
    stored = db_session.get(Analysis, meal['id'])
    assert stored.status == 'confirmed'
    assert stored.confirmed_at is not None
    assert stored.calories == meal['calories']
