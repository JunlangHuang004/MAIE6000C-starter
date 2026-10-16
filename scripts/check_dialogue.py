"""Synthetic live workflow check; creates a test meal via an authorized API endpoint."""
import argparse
import time
from copy import deepcopy

import httpx


def check(base_url):
    with httpx.Client(base_url=base_url,timeout=20) as client:
        def request(path, payload=None):
            response = client.post(path,json=payload) if payload is not None else client.get(path)
            response.raise_for_status()
            return response.json()

        def ready(analysis):
            deadline=time.monotonic()+60
            while analysis['status']=='queued' and time.monotonic()<deadline:
                time.sleep(1)
                analysis=request('/analyses/'+analysis['id'])
            assert analysis['status'] in ('completed','needs_input'), analysis.get('error_message')
            return analysis

        def answer(analysis):
            answers={}
            for q in analysis['questions']:
                if q['kind']=='number':
                    answers[q['key']]=180 if q['key']=='0.grams' else 90
                elif q['kind']=='confirm':
                    answers[q['key']]=True
                elif q['kind']=='choice':
                    answers[q['key']]=q['options'][0]['value']
                elif q['kind']=='recipe':
                    recipe=deepcopy(q['recipe'])
                    recipe['ingredients']['oil']=5
                    recipe['ingredients']['sugar']=0
                    recipe['yield_g']=400
                    answers[q['key']]=recipe
                else:
                    raise AssertionError('Synthetic reference dish failed catalogue lookup')
            return ready(request('/analyses/'+analysis['id']+'/reply',{
                'revision':analysis['revision'],'answers':answers})['analysis'])

        meal=ready(request('/analyses',{'food_text':'一份番茄炒蛋，两个水煮鸡蛋',
                                        'mode':'basic'})['analysis'])
        assert meal['status']=='completed' and meal['calories']>0
        basic_calories=meal['calories']
        assert any(d['grams']==100 for d in meal['details'] if d['food_id']=='egg')
        path='/analyses/'+meal['id']
        meal=ready(request(path+'/mode',{'revision':meal['revision'],
                                         'mode':'advanced'})['analysis'])
        assert meal['status']=='needs_input' and meal['calories'] is None
        assert client.post(path+'/confirm',json={'revision':meal['revision']}).status_code==409
        for _ in range(3):
            if meal['status']=='completed':
                break
            meal=answer(meal)
        assert meal['status']=='completed' and meal['calories']<basic_calories
        meal=ready(request(path+'/reply',{'revision':meal['revision'],
            'message':'水煮鸡蛋改成80克去壳熟重，番茄炒蛋仍是180克熟重，采用刚才的配方。'
            '整锅番茄300克、鸡蛋液150克、油5克、糖0克、盐2克，成品400克。'})['analysis'])
        egg=next(d for d in meal['draft'] if d['food_id']=='egg')
        assert egg['grams']==80
        for _ in range(3):
            if meal['status']=='completed':
                break
            meal=answer(meal)
        assert meal['status']=='completed'
        meal=request(path+'/confirm',{'revision':meal['revision']})
        assert meal['status']=='confirmed' and meal['confirmed_at']
        assert request(path)['details']==meal['details']
        assert client.post(path+'/mode',json={'revision':meal['revision'],
                                             'mode':'basic'}).status_code==409
        print('PASS: basic -> advanced questions -> editable recipe -> natural-language correction')
        print('PASS: persisted evidence, confirmation and locked-mode protection')
        print('Synthetic calories:',basic_calories,'->',meal['calories'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://localhost:8000')
    check(parser.parse_args().base_url)
