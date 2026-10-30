"""API/SQLite/worker recipe lifecycle with a controlled internal AI boundary.

These checks execute the real deterministic calculator; they do not claim live
provider extraction, PostgreSQL concurrency or browser acceptance.
"""
from copy import deepcopy

import httpx
import pytest
from sqlalchemy import func, select

from services.common.config import Settings
from services.common.db import make_session_factory
from services.common.meal_engine import KEYS, ExtractedItem, evaluate_mode
from services.common.models import Analysis, Job
from services.worker.app import main as worker


def payload(basis='consumed', revision=1, item_index=0):
    multiplier = 2 if basis == 'batch' else 1
    return {
        'revision': revision, 'item_index': item_index,
        'name': 'My chicken recipe', 'basis': basis, 'accepted': True,
        'ingredients': [
            {'food_id': 'chicken', 'grams': 150 * multiplier},
            {'food_id': 'oil', 'grams': 5 * multiplier},
            {'food_id': 'soy_sauce', 'grams': 10 * multiplier},
        ],
        'batch_yield_g': 600 if basis == 'batch' else None,
        'consumed_g': 150 if basis == 'batch' else None,
    }


@pytest.fixture()
def workflow(client, db_session, monkeypatch):
    monkeypatch.setattr('services.common.config.get_settings', lambda: Settings(
        _env_file=None, nutrition_provider='qwen'))
    monkeypatch.setattr(worker, 'get_session_factory',
                        lambda: make_session_factory(db_session.get_bind()))
    calls = []

    def respond(url, **kwargs):
        value = kwargs['json']
        assert value['draft'], 'Structured recipes must bypass model extraction'
        calls.append(deepcopy(value))
        return httpx.Response(200, request=httpx.Request('POST', url),
                              json=evaluate_mode(value['draft'], value['mode']))

    monkeypatch.setattr(worker.httpx, 'post', respond)

    def seed(mode='basic', extra_unknown=False, rice_grams=100):
        draft = [
            ExtractedItem(name='火星豉油鸡', source_text='火星豉油鸡', grams=200).model_dump(),
            ExtractedItem(name='米饭', source_text='米饭', food_id='rice', grams=rice_grams,
                          weight_basis='cooked', preparation='as_served').model_dump(),
        ]
        if extra_unknown:
            draft.append(ExtractedItem(name='Another unknown dish').model_dump())
        state = evaluate_mode(draft, mode)
        row = Analysis(food_text='火星豉油鸡配米饭', mode=mode, status='needs_input',
                       conversation=[{'role': 'user', 'content': '火星豉油鸡配米饭'}], **state)
        db_session.add(row)
        db_session.commit()
        return '/analyses/' + row.id, deepcopy(draft)

    def run(response):
        assert response.status_code == 200, response.text
        queued = response.json()
        assert queued['analysis']['status'] == 'queued'
        assert all(queued['analysis'][key] is None for key in KEYS)
        worker.process_nutrition_job(queued['job']['id'])
        db_session.expire_all()
        return client.get('/analyses/' + queued['analysis']['id']).json()

    return seed, run, calls


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
@pytest.mark.parametrize('basis,expected', [('consumed', 359.5), ('batch', 244.8)])
def test_structured_recipe_completes_preserves_other_food_and_locks_after_confirm(
        client, db_session, workflow, mode, basis, expected):
    seed, run, calls = workflow
    path, original = seed(mode)
    request = payload(basis)
    meal = run(client.post(path + '/ingredients', json=request))
    assert meal['status'] == 'completed'
    assert meal['calories'] == expected
    assert meal['draft'][1] == original[1]
    assert meal['draft'][0]['food_id'] is None
    assert meal['draft'][0]['original_name'] == '火星豉油鸡'
    assert meal['draft'][0]['custom_recipe']['accepted'] is True
    assert meal['details'][0]['kind'] == 'custom_recipe'
    assert meal['details'][1]['food_id'] == 'rice'
    assert meal['details'][0]['sources']
    assert calls[-1]['draft'] == meal['draft']
    assert client.get(path).json() == meal
    stored = db_session.get(Analysis, meal['id'])
    assert stored.calories == expected
    assert stored.draft == meal['draft']

    old_request = client.post(path + '/ingredients', json=request)
    assert old_request.status_code == 409
    assert client.get(path).json() == meal
    confirmed = client.post(path + '/confirm', json={'revision': meal['revision']})
    assert confirmed.status_code == 200
    saved = confirmed.json()
    assert saved['status'] == 'confirmed' and saved['confirmed_at']
    assert client.get(path).json() == saved
    locked_payload = payload(basis, revision=saved['revision'])
    assert client.post(path + '/ingredients', json=locked_payload).status_code == 409
    assert client.post(path + '/mode', json={
        'revision': saved['revision'], 'mode': 'basic'}).status_code == 409
    assert client.get(path).json() == saved


def test_pending_unknown_stays_incomplete_and_queue_cannot_be_edited(client, workflow):
    seed, run, _ = workflow
    path, original = seed(extra_unknown=True)
    response = client.post(path + '/ingredients', json=payload())
    queued = response.json()['analysis']
    assert client.post(path + '/ingredients', json=payload(
        revision=queued['revision'])).status_code == 409
    state = run(response)
    assert state['status'] == 'needs_input'
    assert state['draft'][1:] == original[1:]
    assert all(state[key] is None for key in KEYS)
    assert state['details'] == []
    assert state['questions'][0]['key'] == '2.food_id'
    assert client.post(path + '/confirm', json={'revision': state['revision']}).status_code == 409


def test_mode_edit_and_other_food_answers_preserve_recipe_facts(client, workflow):
    seed, run, _ = workflow
    path, _ = seed(mode='advanced', rice_grams=None)
    state = run(client.post(path + '/ingredients', json=payload('batch')))
    recipe = deepcopy(state['draft'][0]['custom_recipe'])
    assert state['status'] == 'needs_input'
    assert any(q['key'] == '1.grams' for q in state['questions'])
    state = run(client.post(path + '/reply', json={
        'revision': state['revision'], 'answers': {'1.grams': 100}}))
    assert state['status'] == 'completed' and state['calories'] == 244.8
    assert state['draft'][0]['custom_recipe'] == recipe
    unchanged = deepcopy(state)
    response = client.post(path + '/reply', json={
        'revision': state['revision'], 'message': 'Change the chicken to 50g'})
    assert response.status_code == 422
    assert client.get(path).json() == unchanged
    state = run(client.post(path + '/mode', json={
        'revision': state['revision'], 'mode': 'basic'}))
    assert state['calories'] == 244.8
    assert state['draft'][0]['custom_recipe'] == recipe
    edit = payload('batch', revision=state['revision'])
    edit['consumed_g'] = 300
    state = run(client.post(path + '/ingredients', json=edit))
    assert state['calories'] == 359.5
    assert state['draft'][0]['original_name'] == '火星豉油鸡'


@pytest.mark.parametrize('patch', [
    {'ingredients': [{'food_id': 'missing_food', 'grams': 100}]},
    {'ingredients': [{'food_id': 'dish_001', 'grams': 100}]},
    {'ingredients': [{'food_id': 'chicken', 'grams': 100}, {'food_id': 'chicken', 'grams': 50}]},
    {'ingredients': [{'food_id': 'chicken', 'grams': 0}]},
    {'ingredients': [{'food_id': 'chicken', 'grams': -1}]},
    {'ingredients': [{'food_id': 'chicken', 'grams': 10001}]},
    {'ingredients': [{'food_id': 'chicken', 'grams': True}]},
    {'ingredients': [{'food_id': 'chicken', 'grams': '100'}]},
    {'ingredients': [{'food_id': 'chicken', 'grams': 100, 'calories': 0}]},
    {'ingredients': []},
    {'accepted': False},
    {'calories': 0},
    {'item_index': 2},
    {'item_index': -1},
    {'item_index': True},
    {'basis': 'batch'},
    {'basis': 'batch', 'batch_yield_g': 100, 'consumed_g': 101},
    {'basis': 'consumed', 'batch_yield_g': 100, 'consumed_g': 50},
])
def test_invalid_recipe_payload_cannot_mutate_saved_meal_or_enqueue_job(
        client, db_session, workflow, patch):
    seed, _, calls = workflow
    path, _ = seed()
    before = client.get(path).json()
    before_jobs = db_session.scalar(select(func.count(Job.id)))
    response = client.post(path + '/ingredients', json={**payload(), **patch})
    assert response.status_code == 422, response.text
    assert client.get(path).json() == before
    assert db_session.scalar(select(func.count(Job.id))) == before_jobs
    assert calls == []
