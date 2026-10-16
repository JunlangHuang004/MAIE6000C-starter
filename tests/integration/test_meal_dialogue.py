import httpx
import pytest

from services.common.config import Settings
from services.common.db import make_session_factory
from services.common.meal_engine import ExtractedItem, evaluate
from services.common.models import Analysis
from services.worker.app import main as worker


@pytest.fixture()
def qwen_mode(monkeypatch):
    monkeypatch.setattr('services.common.config.get_settings',
                        lambda: Settings(_env_file=None,nutrition_provider='qwen'))


def test_worker_dialogue_reply_reload_confirm(client,db_session,monkeypatch,qwen_mode):
    monkeypatch.setattr(worker,'get_session_factory',lambda:make_session_factory(db_session.get_bind()))
    initial=[ExtractedItem(name='番茄炒蛋',food_id='dish_001').model_dump()]
    def respond(url,**kwargs):
        draft=kwargs['json'].get('draft') or initial
        return httpx.Response(200,request=httpx.Request('POST',url),json=evaluate(draft))
    monkeypatch.setattr(worker.httpx,'post',respond)
    data=client.post('/analyses',json={'food_text':'我吃了番茄炒蛋'}).json()
    path='/analyses/'+data['analysis']['id']
    worker.process_nutrition_job(data['job']['id'])
    db_session.expire_all()
    state=client.get(path).json()
    assert state['status']=='needs_input'
    assert state['calories'] is None
    assert state['conversation'][-1]['role']=='assistant'
    assert client.post(path+'/confirm',json={'revision':1}).status_code==409
    recipe=next(q['recipe'] for q in state['questions'] if q['kind']=='recipe')
    data=client.post(path+'/reply',json={'revision':1,'answers':{
        '0.grams':200,'0.weight_basis':'cooked','0.recipe':recipe}}).json()
    assert data['analysis']['revision']==2
    assert client.post(path+'/reply',json={'revision':1,'message':'改成100克'}).status_code==409
    worker.process_nutrition_job(data['job']['id'])
    db_session.expire_all()
    state=client.get(path).json()
    assert state['status']=='completed'
    assert state['calories']>0
    assert state['details'][0]['sources']
    assert state['draft'][0]['recipe_confirmed'] is True
    assert client.post(path+'/confirm',json={'revision':2}).json()['status']=='confirmed'
    assert client.post(path+'/reply',json={'revision':3,'message':'再改一下'}).status_code==409


def test_text_correction_preserves_history_and_clears_previous_estimate(
        client,db_session,qwen_mode):
    data=client.post('/analyses',json={'food_text':'番茄炒蛋200克'}).json()['analysis']
    row=db_session.get(Analysis,data['id'])
    row.status='completed'
    row.calories=200
    row.draft=[{'food_id':'dish_001','recipe_confirmed':True}]
    db_session.commit()
    result=client.post('/analyses/'+row.id+'/reply',json={
        'revision':1,'message':'改成150克，少油'}).json()['analysis']
    assert result['calories'] is None
    assert result['draft']==[]
    assert len(result['conversation'])==2
    assert result['conversation'][-1]['content']=='改成150克，少油'


def test_reply_validation_rejects_forged_fields(client,db_session,qwen_mode):
    data=client.post('/analyses',json={'food_text':'吃了鸡蛋'}).json()['analysis']
    row=db_session.get(Analysis,data['id'])
    row.status='needs_input'
    row.draft=[ExtractedItem(name='鸡蛋',food_id='egg').model_dump()]
    db_session.commit()
    path='/analyses/'+row.id+'/reply'
    assert client.post(path,json={'revision':1,'answers':{'0.calories':1}}).status_code==422
    assert client.post(path,json={'revision':1,'message':'   '}).status_code==422
    assert client.post(path,json={'revision':1,'answers':{'0.grams':100},
                                 'message':'同时发文字'}).status_code==422
    assert client.get('/analyses/'+row.id).json()['revision']==1


def test_mode_switch_removes_basic_assumptions_and_locks_confirmed(
        client,db_session,qwen_mode):
    from services.common.meal_engine import evaluate_mode
    data=client.post('/analyses',json={'food_text':'番茄炒蛋','mode':'basic'}).json()['analysis']
    assert data['mode']=='basic'
    row=db_session.get(Analysis,data['id'])
    result=evaluate_mode([ExtractedItem(name='番茄炒蛋',food_id='dish_001').model_dump()],'basic')
    row.status='completed'
    row.draft=result['draft']
    row.calories=result['calories']
    db_session.commit()
    path='/analyses/'+row.id
    reply=client.post(path+'/mode',json={'revision':1,'mode':'advanced'})
    assert reply.status_code==200
    state=reply.json()['analysis']
    assert state['mode']=='advanced' and state['calories'] is None
    assert state['draft'][0]['grams'] is None
    assert client.post(path+'/mode',json={'revision':1,'mode':'basic'}).status_code==409
    db_session.expire_all()
    row=db_session.get(Analysis,row.id)
    row.status='confirmed'
    db_session.commit()
    assert client.post(path+'/mode',json={'revision':2,'mode':'basic'}).status_code==409
