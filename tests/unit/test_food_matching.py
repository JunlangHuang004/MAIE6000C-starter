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
    ('火星豉油鸡', '火星豉油鸡', 'dish_010'),
    ('火星豉油鸡', '清蒸鲤鱼', 'dish_010'),
    ('清蒸鲤鱼', '清蒸鲤鱼', 'dish_010'),
    (None, '清蒸鲤鱼', 'dish_010'),
])
def test_existing_but_wrong_dish_id_never_produces_estimate(
        monkeypatch, mode, source, name, food_id):
    item = {'food_id': food_id, 'name': name, 'grams': 200, 'weight_basis': 'cooked'}
    if source:
        item['source_text'] = source
    result = extract(monkeypatch, '200克火星豉油鸡', [item], mode)
    assert result.details == []
    assert all(getattr(result, k) is None for k in ('calories','protein_g','fat_g','carbs_g'))
    assert result.draft[0]['food_id'] is None
    assert '火星豉油鸡' in result.questions[0]['label']
    assert result.questions[0]['kind'] == 'unsupported'


@pytest.mark.parametrize('text,source,food_id', [
    ('200克火星酱油鸡', '酱油', 'soy_sauce'),
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


@pytest.mark.parametrize('text,expected_name,food_id', [
    ('100克熟白米饭', '熟白米饭', 'rice'),
    ('１００克熟白米飯', '熟白米飯', 'rice'),
    ('200 g cooked white rice, no added oil', 'cooked white rice', 'rice'),
    ('200 g COOKED WHITE RICE, no added oil', 'COOKED WHITE RICE', 'rice'),
    ('100g Hard-boiled egg (without shell)', 'Hard-boiled egg (without shell)', 'egg'),
    ('100克去壳水煮鸡蛋，熟重', '去壳水煮鸡蛋', 'egg'),
    ('200克番茄炒蛋熟重，不加花生，整锅油5克，成品400克', '番茄炒蛋', 'dish_001'),
])
def test_source_with_only_one_food_and_bounded_wrappers_keeps_actual_name(
        text, expected_name, food_id):
    items = ground_food_items([
        ExtractedItem(name=text, source_text=text, food_id=None)], text)
    assert len(items) == 1
    assert items[0].food_id == food_id
    assert items[0].name == expected_name
    assert items[0].source_text == expected_name
    assert expected_name in text


@pytest.mark.parametrize('text', [
    '100克熟白米饭',
    '100 g cooked white rice, no added oil',
])
def test_wrapped_rice_source_can_be_calculated_after_real_history_extraction(monkeypatch, text):
    result = extract(monkeypatch, text, [
        {'food_id':'rice','name':text,'source_text':text,'grams':100},
    ], history=[{'role':'user','content':text}])
    assert result.calories == 130
    assert [item['food_id'] for item in result.draft] == ['rice']


@pytest.mark.parametrize('text,wrong_id', [
    ('200克火星豉油鸡', 'dish_010'),
    ('200克火星酱油鸡', 'soy_sauce'),
    ('100克米饭和200克火星豉油鸡', 'rice'),
    ('100克熟白米饭和100克水煮鸡蛋', 'rice'),
    ('100克米饭和200克米饭', 'rice'),
    ('100克米饭，米饭200克', 'rice'),
    ('100 g cooked white rice and 200 g cooked white rice', 'rice'),
    ('100克米饭炖鸡', 'rice'),
    ('200 g fried cooked white rice', 'rice'),
    ('200 g cooked white rice, mystery sauce', 'rice'),
])
def test_wrapped_source_cannot_hide_unknowns_other_foods_or_repeated_portions(text, wrong_id):
    items = ground_food_items([
        ExtractedItem(name=text, source_text=text, food_id=wrong_id)], text)
    assert items[0].food_id is None


def test_wrapped_source_still_requires_verbatim_user_grounding():
    source = '100 g cooked white rice, no added oil'
    items = ground_food_items([
        ExtractedItem(name=source, source_text=source, food_id='rice')], '100克火星豉油鸡')
    assert items[0].food_id is None
    assert '火星豉油鸡' in items[0].name


def test_mixed_unknown_is_not_lost_or_allowed_partial_total(monkeypatch):
    result = extract(monkeypatch, '100克米饭和200克火星豉油鸡', [
        {'food_id':'rice', 'name':'米饭','source_text':'米饭','grams':100},
        {'food_id':'dish_010','name':'火星豉油鸡','source_text':'火星豉油鸡','grams':200},
    ])
    assert [item['food_id'] for item in result.draft] == ['rice', None]
    assert result.calories is None and result.details == []


def test_invented_catalogue_id_has_the_same_no_record_result(monkeypatch):
    result = extract(monkeypatch, '200克火星豉油鸡', [{
        'food_id':'invented_soy_chicken', 'name':'火星豉油鸡',
        'source_text':'火星豉油鸡','grams':200,
    }])
    assert result.calories is None
    assert result.questions[0]['kind'] == 'unsupported'


def test_omitted_unknown_clause_cannot_turn_into_partial_meal(monkeypatch):
    result = extract(monkeypatch, '100克米饭和200克火星豉油鸡', [
        {'food_id':'rice','name':'米饭','source_text':'米饭','grams':100},
    ])
    assert [item['food_id'] for item in result.draft] == ['rice', None]
    assert '火星豉油鸡' in result.questions[0]['label']
    assert result.calories is None


@pytest.mark.parametrize('text,history', [
    ('100克米饭', [{'role':'user', 'content':'另外200克火星豉油鸡'}]),
    ('100克米饭，整锅火星豉油鸡200克', None),
    ('100克米饭，不加油的火星豉油鸡200克', None),
])
def test_unknown_additions_and_detail_like_food_names_cannot_be_dropped(
        monkeypatch, text, history):
    result = extract(monkeypatch, text, [
        {'food_id':'rice','name':'米饭','source_text':'米饭','grams':100},
    ], history=history)
    assert result.calories is None
    assert any('火星豉油鸡' in q['label'] and q['kind'] == 'unsupported' for q in result.questions)


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
    assert ground_food_items([item], '火星豉油鸡', history)[0].food_id is None


def test_quantity_correction_retains_source_but_identity_replacement_does_not():
    def meal():
        return [ExtractedItem(name='番茄炒蛋', source_text='番茄炒蛋', food_id='dish_001')]
    assert ground_food_items(meal(), '200克番茄炒蛋', [
        {'role':'user','content':'改成150克，少油'},
    ])[0].food_id == 'dish_001'
    assert ground_food_items(meal(), '200克番茄炒蛋', [
        {'role':'user','content':'改成200克火星豉油鸡'},
    ])[0].food_id is None


def test_natural_portion_correction_does_not_turn_weight_details_into_foods(monkeypatch):
    result = extract(monkeypatch, '一份番茄炒蛋，两个水煮鸡蛋', [
        {'food_id':'dish_001','name':'番茄炒蛋','source_text':'番茄炒蛋','grams':150},
        {'food_id':'egg','name':'水煮鸡蛋','source_text':'水煮鸡蛋','grams':100},
    ], history=[{'role':'user',
                'content':'番茄炒蛋实际吃了150克熟重，水煮鸡蛋可食部分还是100克。'}])
    assert result.calories is not None
    assert [i['food_id'] for i in result.draft] == ['dish_001', 'egg']
    assert [i['grams'] for i in result.draft] == [150, 100]


def test_common_cooked_white_rice_name_is_a_reviewed_alias(monkeypatch):
    result = extract(monkeypatch, '100克熟白米饭', [
        {'food_id':'rice','name':'熟白米饭','source_text':'熟白米饭','grams':100}])
    assert result.calories == 130


def test_unknown_dish_can_be_replaced_by_explicit_consumed_ingredients(monkeypatch):
    reply = '改成这次实际吃下的食材：生鸡胸肉150克、食用油5克、酱油10克'
    result = extract(monkeypatch, '火星豉油鸡200克', [
        {'food_id':'chicken','name':'生鸡胸肉','source_text':'生鸡胸肉','grams':150},
        {'food_id':'oil','name':'食用油','source_text':'食用油','grams':5},
        {'food_id':'soy_sauce','name':'酱油','source_text':'酱油','grams':10},
    ], history=[{'role':'user','content':reply}])
    assert result.calories is not None
    assert [i['food_id'] for i in result.draft] == ['chicken', 'oil', 'soy_sauce']
    assert [i['grams'] for i in result.draft] == [150, 5, 10]


@pytest.mark.parametrize('replacement', [
    '改成这次实际吃下的食材：生鸡胸肉150克',
    '这次实际吃下的食材：生鸡胸肉150克',
    '改成生鸡胸肉150克',
    'Replace the meal with 生鸡胸肉150克',
])
def test_multiline_replacement_keeps_unsupported_trailing_food(monkeypatch, replacement):
    result = extract(monkeypatch, '火星豉油鸡200克', [
        {'food_id':'chicken','name':'生鸡胸肉','source_text':'生鸡胸肉','grams':150},
    ], history=[{'role':'user','content':replacement + '\n另外200克火星豉油鸡'}])
    assert result.calories is None and result.details == []
    assert any('火星豉油鸡' in q['label'] and q['kind'] == 'unsupported' for q in result.questions)


@pytest.mark.parametrize('replacement', [
    '改成这次实际吃下的食材：生鸡胸肉150克',
    '改成生鸡胸肉150克',
])
def test_replacement_stays_current_after_later_portion_correction(monkeypatch, replacement):
    result = extract(monkeypatch, '火星豉油鸡200克', [
        {'food_id':'chicken','name':'生鸡胸肉','source_text':'生鸡胸肉','grams':120},
    ], history=[
        {'role':'user','content':replacement},
        {'role':'user','content':'改成120克'},
        {'role':'user','content':'生鸡胸肉实际吃了120克生重'},
    ])
    assert result.calories == 144
    assert [item['food_id'] for item in result.draft] == ['chicken']


@pytest.mark.parametrize('replacement', [
    '改成这次实际吃下的食材：生鸡胸肉150克',
    '改成生鸡胸肉150克',
])
def test_replacement_keeps_later_unknown_additions_and_portion_reply(monkeypatch, replacement):
    result = extract(monkeypatch, '火星豉油鸡200克', [
        {'food_id':'chicken','name':'生鸡胸肉','source_text':'生鸡胸肉','grams':120},
    ], history=[
        {'role':'user','content':replacement},
        {'role':'user','content':'另外200克火星豉油鸡'},
        {'role':'user','content':'改成120克'},
    ])
    assert result.calories is None and result.details == []
    assert any('火星豉油鸡' in q['label'] and q['kind'] == 'unsupported' for q in result.questions)


@pytest.mark.parametrize('reply', [
    '另外200克火星豉油鸡，改成这次实际吃下的食材：生鸡胸肉150克',
    '不要改成这次实际吃下的食材：生鸡胸肉150克',
    '另外200克火星豉油鸡，改成生鸡胸肉150克',
])
def test_embedded_or_negated_replacement_does_not_discard_other_foods(monkeypatch, reply):
    result = extract(monkeypatch, '火星豉油鸡200克', [
        {'food_id':'chicken','name':'生鸡胸肉','source_text':'生鸡胸肉','grams':150},
    ], history=[{'role':'user','content':reply}])
    assert result.calories is None and result.details == []
    assert any(q['kind'] == 'unsupported' for q in result.questions)


def test_whole_pot_ingredient_list_does_not_resolve_unknown_dish_as_personal_intake():
    items = [ExtractedItem(name='生鸡胸肉', source_text='生鸡胸肉', food_id='chicken', grams=500)]
    result = ground_food_items(items, '火星豉油鸡200克', [
        {'role':'user','content':'整锅食材是生鸡胸肉500克，成品800克，我吃了200克'}])
    assert any(item.food_id is None for item in result)


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
    assert '火星豉油鸡' not in name_index() and '火星酱油鸡' not in name_index()


@pytest.mark.parametrize('name', ['豉油鸡', '酱油鸡', '豉油雞', '醬油雞'])
def test_new_soy_chicken_reference_never_uses_the_old_wrong_fish_id(monkeypatch, name):
    result = extract(monkeypatch, '200克' + name, [{
        'food_id':'dish_010', 'name':'清蒸鲤鱼', 'source_text':name, 'grams':200,
    }])
    assert result.calories is not None
    assert result.draft[0]['food_id'] == 'dish_251'
    assert result.details[0]['food_id'] == 'dish_251'
    assert any('参考配方' in note for note in result.details[0]['assumptions'])


@pytest.mark.parametrize('name,food_id,detail', [
    ('可乐鸡翅', 'dish_252', '（已去骨）'),
    ('可乐鸡翅', 'dish_252', '(已去骨)'),
    ('水煮鸡蛋', 'egg', '（已去壳）'),
    ('水煮鸡蛋', 'egg', '(已去殼)'),
])
@pytest.mark.parametrize('include_wrapper', [False, True])
def test_known_food_with_explicit_removed_bones_or_shells_is_still_grounded(
        name, food_id, detail, include_wrapper):
    text = name + '75克熟重' + detail
    source = text if include_wrapper else name
    items = ground_food_items([ExtractedItem(
        name=name, source_text=source, food_id='dish_010', grams=75)], text)
    assert len(items) == 1 and items[0].food_id == food_id
    assert items[0].source_text == name


@pytest.mark.parametrize('suffix', ['（已去骨月球紫晶兽肉）', '（已月球紫晶兽肉）'])
def test_removed_bone_wrapper_does_not_discard_an_unknown_food(suffix):
    items = ground_food_items([ExtractedItem(
        name='可乐鸡翅', source_text='可乐鸡翅', food_id='dish_252', grams=75)],
        '可乐鸡翅75克熟重' + suffix)
    assert any(item.food_id is None for item in items)
