import os
import time

import httpx
import pytest

pytestmark = pytest.mark.smoke


def test_smoke_meal_review_flow():
    base = os.getenv('SMOKE_BASE_URL')
    if not base:
        pytest.skip('SMOKE_BASE_URL not set')
    with httpx.Client(base_url=base, timeout=10) as client:
        created = client.post('/analyses', json={'food_text': '100g egg'})
        assert created.status_code == 201
        path = '/analyses/' + created.json()['analysis']['id']

        def completed():
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                response = client.get(path)
                response.raise_for_status()
                row = response.json()
                assert row['status'] != 'failed', row
                if row['status'] == 'completed':
                    return row
                time.sleep(0.5)
            pytest.fail('Nutrition worker did not complete in 60 seconds')

        initial = completed()
        assert initial['calories'] == 155
        corrected = client.patch(path, json={
            'food_text': '200g egg', 'revision': initial['revision'],
        })
        assert corrected.status_code == 200
        result = completed()
        assert result['calories'] == 310
        assert result['protein_g'] == 26
        assert result['fat_g'] == 22
        assert result['carbs_g'] == 2.2
        assert result['interpreted_food_text']
        confirmed = client.post(path+'/confirm', json={'revision': result['revision']})
        assert confirmed.status_code == 200
        assert confirmed.json()['status'] == 'confirmed'
        assert confirmed.json()['confirmed_at']
        assert client.get(path).json() == confirmed.json()
