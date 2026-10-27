"""Opt-in real-Qwen catalogue check; creates two synthetic meal records."""
import argparse
from copy import deepcopy
import time

from services.common.http_auth import CheckAuthenticationError, authenticated_client


def check(base_url):
    with authenticated_client(base_url, timeout=25) as client:
        def post(path, data):
            response = client.post(path, json=data)
            response.raise_for_status()
            return response.json()

        def get(path):
            response = client.get(path)
            response.raise_for_status()
            return response.json()

        def ready(meal):
            deadline = time.monotonic()+150
            while meal['status'] == 'queued' and time.monotonic() < deadline:
                time.sleep(1)
                meal = get('/analyses/'+meal['id'])
            assert meal['status'] in ('completed', 'needs_input'), meal.get('error_message')
            return meal

        def approve(meal):
            answers = {}
            for question in meal['questions']:
                key = question['key']
                if question['kind'] == 'number':
                    answers[key] = 180
                elif question['kind'] == 'confirm':
                    answers[key] = True
                elif question['kind'] == 'choice':
                    answers[key] = question['options'][0]['value']
                elif question['kind'] == 'recipe':
                    recipe = deepcopy(question['recipe'])
                    if 'oil' in recipe['ingredients']:
                        recipe['ingredients']['oil'] = 5
                    answers[key] = recipe
                else:
                    raise AssertionError('A supported synthetic dish was not matched')
            return ready(post('/analyses/'+meal['id']+'/reply', {
                'revision':meal['revision'], 'answers':answers})['analysis'])

        meal = ready(post('/analyses', {
            'food_text':'测试餐：十个白菜猪肉饺子，另外200克青椒牛肉熟重。',
            'mode':'basic'})['analysis'])
        assert meal['status'] == 'completed'
        by_name = {detail['name']: detail for detail in meal['details']}
        assert by_name['白菜猪肉饺子']['grams'] == 200
        assert by_name['青椒牛肉']['grams'] == 200
        path = '/analyses/'+meal['id']
        meal = ready(post(path+'/mode', {
            'revision':meal['revision'], 'mode':'advanced'})['analysis'])
        assert meal['status'] == 'needs_input' and meal['calories'] is None
        assert client.post(path+'/confirm', json={
            'revision':meal['revision']}).status_code == 409
        meal = approve(meal)
        assert meal['status'] == 'completed'
        approved = {item['food_id']: item for item in meal['draft']}
        assert approved['dish_086']['recipe']['ingredients']['oil'] == 5
        assert approved['dish_241']['recipe']['ingredients']['sesame_oil'] == 10
        meal = ready(post(path+'/reply', {
            'revision':meal['revision'],
            'message':'白菜猪肉饺子改成160克熟重；青椒牛肉仍为200克熟重。'
                      '青椒牛肉整锅油5克，整锅成品450克。'})['analysis'])
        by_id = {item['food_id']: item for item in meal['draft']}
        assert by_id['dish_241']['grams'] == 160
        assert by_id['dish_086']['recipe_ingredients']['oil'] == 5
        assert by_id['dish_086']['recipe_yield_g'] == 450
        if meal['status'] == 'needs_input':
            meal = approve(meal)
        assert meal['status'] == 'completed'
        confirmed = post(path+'/confirm', {'revision':meal['revision']})
        assert confirmed['status'] == 'confirmed'
        assert get(path)['details'] == confirmed['details']
        assert client.post(path+'/mode', json={
            'revision':confirmed['revision'], 'mode':'basic'}).status_code == 409
        print('PASS: new dishes, piece weights, mode switch, recipe edits, '
              'natural-language correction, save, reload and confirmation lock', flush=True)

        bone = ready(post('/analyses', {
            'food_text':'测试餐：200克糖醋排骨，200克包含骨头，不知道去骨后克数。',
            'mode':'basic'})['analysis'])
        assert bone['status'] == 'completed' and not bone['questions']
        assert bone['draft'][0]['grams'] == 200
        assert bone['draft'][0]['weight_includes_inedible'] is True
        assert bone['details'][0]['grams'] == 120
        assert '60%' in ' '.join(bone['details'][0]['assumptions'])
        bone_path = '/analyses/'+bone['id']
        advanced = ready(post(bone_path+'/mode', {
            'revision':bone['revision'], 'mode':'advanced'})['analysis'])
        assert advanced['status'] == 'needs_input' and advanced['calories'] is None
        assert any(q['key'] == '0.grams' for q in advanced['questions'])
        print('PASS: basic gross-weight estimate stays labelled; advanced asks for net grams',
              flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://localhost:8000')
    parser.add_argument('--live', action='store_true',
                        help='Use model quota and create synthetic meal records')
    args = parser.parse_args()
    if not args.live:
        parser.error('--live is required to use model quota and create records')
    try:
        check(args.base_url)
    except CheckAuthenticationError as exc:
        parser.exit(2, f"Check authentication failed: {exc}\n")
