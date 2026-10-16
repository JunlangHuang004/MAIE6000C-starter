import pytest

from services.common.models import Analysis, Job
from services.common.nutrition import estimate_meal
from services.common.db import make_session_factory
from services.worker.app import main as worker


def complete(client, db_session, analysis_id):
    row = db_session.get(Analysis, analysis_id)
    for key, value in estimate_meal(row.food_text).items():
        setattr(row, key, value)
    row.status = 'completed'
    db_session.commit()
    return client.get(f'/analyses/{analysis_id}').json()


def test_correct_recalculate_confirm(client, db_session):
    initial = client.post('/analyses', json={'food_text': '100g egg'}).json()['analysis']
    path = '/analyses/' + initial['id']
    assert client.post(path+'/confirm', json={'revision': 1}).status_code == 409
    complete(client, db_session, initial['id'])
    corrected = client.patch(path, json={'food_text': '200g egg', 'revision': 1})
    assert corrected.status_code == 200
    assert corrected.json()['analysis']['revision'] == 2
    assert corrected.json()['analysis']['calories'] is None
    assert db_session.query(Job).count() == 2
    assert client.patch(path, json={'food_text': '300g egg', 'revision': 1}).status_code == 409
    result = complete(client, db_session, initial['id'])
    assert result['calories'] == 310
    assert client.post(path+'/confirm', json={'revision': 1}).status_code == 409
    confirmed = client.post(path+'/confirm', json={'revision': 2})
    assert confirmed.status_code == 200
    assert confirmed.json()['status'] == 'confirmed'
    assert confirmed.json()['confirmed_at'] is not None
    assert client.get(path).json() == confirmed.json()
    assert client.patch(path, json={'food_text': '300g egg', 'revision': 3}).status_code == 409


@pytest.mark.parametrize('meal', ['100g pizza', '100g egg and 50g tofu', '-1g egg',
                                  '0g rice', '10001g rice', 'rice', '100g egg junk'])
def test_invalid_meal_writes_nothing(client, db_session, meal):
    assert client.post('/analyses', json={'food_text': meal}).status_code == 422
    assert db_session.query(Analysis).count() == 0
    assert db_session.query(Job).count() == 0


def test_worker_failure_can_be_corrected(client, db_session, monkeypatch):
    factory = make_session_factory(db_session.get_bind())
    monkeypatch.setattr(worker, 'get_session_factory', lambda: factory)
    data = client.post('/analyses', json={'food_text': '100g egg'}).json()
    worker.mark_job_failed(data['job']['id'], 'upstream timeout')
    db_session.expire_all()
    path = '/analyses/' + data['analysis']['id']
    assert client.get(path).json()['status'] == 'failed'
    assert client.post(path+'/confirm', json={'revision': 1}).status_code == 409
    assert client.patch(path, json={'food_text': '200g egg', 'revision': 1}).status_code == 200


def test_review_missing_record(client):
    assert client.post('/analyses/missing/confirm', json={'revision': 1}).status_code == 404
    assert client.patch('/analyses/missing', json={
        'food_text': '100g egg', 'revision': 1,
    }).status_code == 404


def test_foods_and_ui(client):
    assert 'chicken breast' in client.get('/foods').json()['foods']
    assert 'NutriChat' in client.get('/app').text
