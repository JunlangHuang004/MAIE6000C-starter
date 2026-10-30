import json

import httpx
import pytest
from pydantic import SecretStr

from services.ai.app.qwen import analyze_with_qwen
from services.common.config import Settings
from services.common.food_matching import ground_food_items, matching_aliases, name_index
from services.common.meal_engine import ExtractedItem, catalogue


def extract(monkeypatch, text, items, mode='basic', history=None):
    def respond(url, **kwargs):
        prompt = kwargs['json']['messages'][0]['content']
        assert 'source_text' in prompt
        assert '巧克力可选牛奶巧克力' not in prompt
        return httpx.Response(200, request=httpx.Request('POST', url), json={
            'choices': [{'finish_reason': 'stop', 'message': {
                'content': json.dumps({'items': items}, ensure_ascii=False)}}]})
    monkeypatch.setattr('services.ai.app.qwen.httpx.post', respond)
    config = Settings(_env_file=None, nutrition_provider='qwen',
                      dashscope_api_key=SecretStr('fake-key'),
                      qwen_base_url='https://example.test/v1')
    return analyze_with_qwen(text, config, history, mode)


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
@pytest.mark.parametrize('source,name,food_id', [
    ('豉油鸡', '豉油鸡', 'dish_010'),
    ('豉油鸡', '清蒸鲤鱼', 'dish_010'),
    ('清蒸鲤鱼', '清蒸鲤鱼', 'dish_010'),
    (None, '清蒸鲤鱼', 'dish_010'),
])
def test_existing_but_wrong_dish_id_never_produces_estimate(
        monkeypatch, mode, source, name, food_id):
    item = {'food_id': food_id, 'name': name, 'grams': 200, 'weight_basis': 'cooked'}
    if source:
        item['source_text'] = source
    result = extract(monkeypatch, '200克豉油鸡', [item], mode)
    assert result.details == []
    assert all(getattr(result, k) is None for k in ('calories','protein_g','fat_g','carbs_g'))
    assert result.draft[0]['food_id'] is None
    assert '豉油鸡' in result.questions[0]['label']
    assert result.questions[0]['kind'] == 'unsupported'


@pytest.mark.parametrize('text,source,food_id', [
    ('200克酱油鸡', '酱油', 'soy_sauce'),
    ('200克番茄炒蛋', '番茄', 'tomato'),
    ('200克蒜蓉芥蓝', '芥蓝', 'gai_lan'),
])
def test_cannot_use_ingredient_substring_or_similar_vegetable(text, source, food_id):
    item = ExtractedItem(name=source, source_text=source, food_id=food_id)
    assert ground_food_items([item], text)[0].food_id is None


def test_unique_exact_record_overrides_wrong_model_id_without_using_a_substitute():
    source = 'garlic stir-fried Chinese broccoli (gai lan)'
    items = ground_food_items([
        ExtractedItem(name=source, source_text=source, food_id='dish_017')], '200g '+source)
    assert [item.food_id for item in items] == ['dish_144']


@pytest.mark.parametrize('text,source,food_id', [
    ('200克番茄炒蛋熟重', '番茄炒蛋', 'dish_001'),
    ('我吃了一份西红柿炒鸡蛋', '西红柿炒鸡蛋', 'dish_001'),
    ('两个水煮鸡蛋', '水煮鸡蛋', 'egg'),
    ('100克去壳水煮鸡蛋，熟重', '水煮鸡蛋', 'egg'),
    ('200g of the Chinese dish tomato-and-egg stir-fry, cooked edible weight.',
     'tomato-and-egg stir-fry', 'dish_001'),
    ('250g Kung Pao chicken, cooked edible weight.', 'Kung Pao chicken', 'dish_003'),
    ('200g garlic stir-fried Chinese broccoli (gai lan)',
     'garlic stir-fried Chinese broccoli (gai lan)', 'dish_144'),
])
def test_reviewed_exact_chinese_and_english_mentions_remain_supported(text, source, food_id):
    items = ground_food_items([ExtractedItem(name=source, source_text=source, food_id=food_id)],
                             text)
    assert [item.food_id for item in items] == [food_id]


def test_mixed_unknown_is_not_lost_or_allowed_partial_total(monkeypatch):
    result = extract(monkeypatch, '100克米饭和200克豉油鸡', [
        {'food_id':'rice', 'name':'米饭','source_text':'米饭','grams':100},
        {'food_id':'dish_010','name':'豉油鸡','source_text':'豉油鸡','grams':200},
    ])
    assert [item['food_id'] for item in result.draft] == ['rice', None]
    assert result.calories is None and result.details == []


def test_invented_catalogue_id_has_the_same_no_record_result(monkeypatch):
    result = extract(monkeypatch, '200克豉油鸡', [{
        'food_id':'invented_soy_chicken', 'name':'豉油鸡','source_text':'豉油鸡','grams':200,
    }])
    assert result.calories is None
    assert result.questions[0]['kind'] == 'unsupported'


def test_omitted_unknown_clause_cannot_turn_into_partial_meal(monkeypatch):
    result = extract(monkeypatch, '100克米饭和200克豉油鸡', [
        {'food_id':'rice','name':'米饭','source_text':'米饭','grams':100},
    ])
    assert [item['food_id'] for item in result.draft] == ['rice', None]
    assert '豉油鸡' in result.questions[0]['label']
    assert result.calories is None


@pytest.mark.parametrize('text,history', [
    ('100克米饭', [{'role':'user', 'content':'另外200克豉油鸡'}]),
    ('100克米饭，整锅豉油鸡200克', None),
    ('100克米饭，不加油的豉油鸡200克', None),
])
def test_unknown_additions_and_detail_like_food_names_cannot_be_dropped(
        monkeypatch, text, history):
    result = extract(monkeypatch, text, [
        {'food_id':'rice','name':'米饭','source_text':'米饭','grams':100},
    ], history=history)
    assert result.calories is None
    assert any('豉油鸡' in q['label'] and q['kind'] == 'unsupported' for q in result.questions)


@pytest.mark.parametrize('text,source,food_id', [
    ('100g raw chicken breast, edible weight measured before cooking.',
     'raw chicken breast', 'chicken'),
    ('100g roasted chicken breast, with 0g additional oil in this portion.',
     'roasted chicken breast', 'chicken_roast'),
    ('100g hard-boiled egg, shells removed, with no added oil.', 'hard-boiled egg', 'egg'),
    ('One bowl of steamed white rice, with no added oil.', 'steamed white rice', 'rice'),
    ('100g boiled broccoli. All weights are cooked edible weights.',
     'boiled broccoli', 'broccoli_cooked'),
])
def test_bounded_english_details_do_not_create_extra_foods(text, source, food_id):
    items = ground_food_items([ExtractedItem(name=source, source_text=source, food_id=food_id)],
                             text)
    assert [item.food_id for item in items] == [food_id]


def test_assistant_and_copied_draft_cannot_supply_matching_evidence():
    history = [
        {'role':'assistant','content':'请选择清蒸鲤鱼'},
        {'role':'user','content':'已回答：{}\n当前餐食资料：[{"catalogue_name":"清蒸鲤鱼"}]'},
    ]
    item = ExtractedItem(name='清蒸鲤鱼', source_text='清蒸鲤鱼', food_id='dish_010')
    assert ground_food_items([item], '豉油鸡', history)[0].food_id is None


def test_quantity_correction_retains_source_but_identity_replacement_does_not():
    def meal():
        return [ExtractedItem(name='番茄炒蛋', source_text='番茄炒蛋', food_id='dish_001')]
    assert ground_food_items(meal(), '200克番茄炒蛋', [
        {'role':'user','content':'改成150克，少油'},
    ])[0].food_id == 'dish_001'
    assert ground_food_items(meal(), '200克番茄炒蛋', [
        {'role':'user','content':'改成200克豉油鸡'},
    ])[0].food_id is None


def test_recipe_corrections_are_not_unsupported_extra_foods(monkeypatch):
    result = extract(monkeypatch, '200克宫保鸡丁熟重，不加花生，整锅油5克，成品400克', [{
        'food_id':'dish_003','name':'宫保鸡丁','source_text':'宫保鸡丁','grams':200,
        'weight_basis':'cooked','recipe_ingredients':{'peanut':0,'oil':5},'recipe_yield_g':400,
    }])
    assert result.calories is not None and len(result.draft) == 1
    assert result.draft[0]['recipe_ingredients'] == {'peanut':0,'oil':5}


def test_aliases_are_explicit_unique_and_keep_catalogue_identity():
    foods = {f['id'] for f in catalogue()['foods']}
    assert set(matching_aliases()) == foods
    assert all(len(ids) == 1 for ids in name_index().values())
    assert name_index()['蒜蓉芥蓝'] == {'dish_144'}
    assert '豉油鸡' not in name_index() and '酱油鸡' not in name_index()
