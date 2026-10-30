import json

import httpx
import pytest
from pydantic import SecretStr

from services.ai.app.qwen import analyze_with_qwen
from services.common.config import Settings
from services.common.nutrition import estimate_meal


def test_repeated_foods_and_decimals():
    assert estimate_meal('50g egg and 50g egg') == estimate_meal('100g egg')
    assert estimate_meal('100g white rice')['calories'] == 130
    assert estimate_meal('12.5 grams broccoli')['calories'] == 4.4


def config():
    return Settings(_env_file=None, nutrition_provider='qwen',
                    dashscope_api_key=SecretStr('test-key'), qwen_base_url='https://example.test/v1')


def mock_qwen(monkeypatch, content, finish='stop'):
    def respond(url, **kwargs):
        assert url.endswith('/chat/completions')
        assert kwargs['json']['response_format'] == {'type': 'json_object'}
        return httpx.Response(200, request=httpx.Request('POST', url), json={
            'choices': [{'finish_reason': finish, 'message': {'content': content}}],
        })
    monkeypatch.setattr('services.ai.app.qwen.httpx.post', respond)


def test_qwen_calculates_from_catalogue(monkeypatch):
    from services.common.meal_engine import catalogue
    mock_qwen(monkeypatch, json.dumps({'items': [{
        'food_id':'egg', 'name':'水煮鸡蛋', 'grams':100,
        'weight_basis':'cooked', 'preparation':'boiled',
    }]}))
    result = analyze_with_qwen('100克去壳水煮鸡蛋，熟重', config())
    egg = next(f for f in catalogue()['foods'] if f['id']=='egg')
    assert result.calories == egg['nutrients']['calories']
    assert '水煮鸡蛋' in result.interpreted_food_text
    assert result.questions == []


@pytest.mark.parametrize('content', [
    'not json', '{"items":[{"food":"pizza","grams":100}],"error":null}',
    '{"items":[{"food":"egg","grams":-1}],"error":null}',
    '{"items":[{"food":"egg","grams":100,"calories":1}],"error":null}',
])
def test_qwen_rejects_invalid_output(monkeypatch, content):
    mock_qwen(monkeypatch, content)
    with pytest.raises(RuntimeError, match='格式不正确'):
        analyze_with_qwen('meal', config())


def test_qwen_asks_for_unsupported_meal(monkeypatch):
    mock_qwen(monkeypatch, '{"items":[{"food_id":null,"name":"未知披萨","grams":100}]}')
    result = analyze_with_qwen('100g pizza', config())
    assert result.calories is None
    assert result.questions[0]['kind'] == 'unsupported'


def test_qwen_timeout_does_not_fabricate_result(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout('timeout')
    monkeypatch.setattr('services.ai.app.qwen.httpx.post', timeout)
    with pytest.raises(RuntimeError, match='暂时不可用'):
        analyze_with_qwen('100g egg', config())


def test_model_piece_count_is_not_accepted_as_an_unstated_gram_weight(monkeypatch):
    mock_qwen(monkeypatch, json.dumps({'items':[{
        'food_id':'dish_241', 'name':'白菜猪肉饺子', 'grams':10,
        'portion_count':10, 'portion_unit':'piece',
    }]}))
    result = analyze_with_qwen('十个白菜猪肉饺子', config(), mode='basic')
    assert result.draft[0]['grams'] is None
    assert result.details[0]['grams'] == 200


@pytest.mark.parametrize('text', ['十克白菜猪肉饺子，共十个', '10g白菜猪肉饺子，共十个'])
def test_explicit_grams_equal_to_piece_count_are_preserved(monkeypatch, text):
    mock_qwen(monkeypatch, json.dumps({'items':[{
        'food_id':'dish_241', 'name':'白菜猪肉饺子', 'grams':10,
        'portion_count':10, 'portion_unit':'piece',
    }]}))
    result = analyze_with_qwen(text, config(), mode='basic')
    assert result.draft[0]['grams'] == 10
    assert result.details[0]['grams'] == 10


def test_weight_evidence_excludes_assistant_suggestions():
    from services.ai.app.qwen import _explicit_weights
    assert _explicit_weights('十个饺子', [
        {'role':'assistant', 'content':'是否每个10克？'},
        {'role':'user', 'content':'另有半斤牛肉和0.2kg米饭，菜是二百五十克。'},
    ]) == {250, 200}
