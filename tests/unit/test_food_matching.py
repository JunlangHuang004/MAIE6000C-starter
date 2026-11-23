import json

import httpx
import pytest
from pydantic import SecretStr

from services.ai.app.qwen import analyze_with_qwen
from services.common.config import Settings
from services.common.food_matching import ground_food_items, matching_aliases, name_index
from services.common.meal_engine import ExtractedItem, catalogue, evaluate


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


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
@pytest.mark.parametrize('text,chicken_g,rice_g', [
    ('500g手撕鸡200g米饭', 500, 200),
    ('500g手撕鸡 200g米饭', 500, 200),
    ('500g 手撕鸡   200g 米饭', 500, 200),
    ('500g手撕鸡\t200g米饭', 500, 200),
    ('500.5g手撕鸡200.25g米饭', 500.5, 200.25),
    ('５００ｇ手撕鸡２００ｇ米饭', 500, 200),
    ('我吃了500克手撕鸡200克米饭', 500, 200),
    ('0.5kg手撕鸡0.2公斤米饭', 500, 200),
])
def test_quantity_led_lists_ground_both_foods_without_punctuation(
        monkeypatch, mode, text, chicken_g, rice_g):
    result = extract(monkeypatch, text, [
        {'name':'手撕鸡','source_text':'手撕鸡','food_id':'dish_255','grams':chicken_g},
        {'name':'米饭','source_text':'米饭','food_id':'rice','grams':rice_g},
    ], mode)
    assert [item['food_id'] for item in result.draft] == ['dish_255', 'rice']
    assert [item['grams'] for item in result.draft] == [chicken_g, rice_g]
    assert not any(q['kind'] == 'unsupported' for q in result.questions)
    if mode == 'basic':
        assert result.calories is not None and result.calories > 0
        assert len(result.details) == 2
    else:
        assert result.calories is None
        assert any(q['kind'] == 'recipe' for q in result.questions)


@pytest.mark.parametrize('text', [
    '250g Kung Pao chicken 200g cooked white rice',
    '250g tomato-and-egg stir-fry 200g cooked white rice',
])
def test_compact_lists_preserve_whole_multiword_english_food_names(text):
    source = text[5:text.index(' 200g')]
    expected = 'dish_003' if source == 'Kung Pao chicken' else 'dish_001'
    items = ground_food_items([
        ExtractedItem(name=source, source_text=source, grams=250),
        ExtractedItem(name='cooked white rice', source_text='cooked white rice', grams=200),
    ], text)
    assert [item.food_id for item in items] == [expected, 'rice']


@pytest.mark.parametrize('text,mention', [
    ('500g火星手撕鸡200g米饭', '手撕鸡'),
    ('100g番茄炒蛋200g米饭', '番茄'),
    ('100g番茄炒蛋200g米饭', '蛋'),
    ('200g fried cooked white rice100g水煮鸡蛋', 'cooked white rice'),
    ('500g手撕鸡-200g米饭', '米饭'),
    ('500g手撕鸡2.5.0g米饭', '米饭'),
])
def test_compact_list_fallback_does_not_authorize_partial_names_or_bad_mass(text, mention):
    items = ground_food_items([ExtractedItem(name=mention, source_text=mention)], text)
    assert items[0].food_id is None


@pytest.mark.parametrize('text', [
    '500g火星手撕鸡200g米饭',
    '200g米饭500g火星手撕鸡',
    '200g米饭 500g未知蔬菜',
])
def test_compact_list_cannot_drop_unknown_siblings(monkeypatch, text):
    result = extract(monkeypatch, text, [
        {'name':'米饭','source_text':'米饭','food_id':'rice','grams':200},
    ])
    assert result.calories is None and result.details == []
    assert any(q['kind'] == 'unsupported' for q in result.questions)


@pytest.mark.parametrize('text', [
    '500g手撕鸡200g米饭', '100g米饭200g米饭',
    '500g手撕鸡200g未知食物',
])
def test_compact_multi_food_source_is_not_collapsed_into_one_record(text):
    items = ground_food_items([ExtractedItem(name=text, source_text=text, food_id='rice')],
                             text)
    assert items[0].food_id is None


def test_compact_explicit_replacement_keeps_latest_meal_and_discards_old_identity(monkeypatch):
    text = '改成500g手撕鸡200g米饭'
    result = extract(monkeypatch, '100g火星豉油鸡', [
        {'name':'手撕鸡','source_text':'手撕鸡','food_id':'dish_255','grams':500},
        {'name':'米饭','source_text':'米饭','food_id':'rice','grams':200},
    ], history=[{'role':'user','content':'100g火星豉油鸡'},
                {'role':'user','content':text}])
    assert [item['food_id'] for item in result.draft] == ['dish_255','rice']
    assert result.calories == 847.4


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


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
@pytest.mark.parametrize('correction', [
    '更正：不要番茄炒蛋了，只吃了100克水煮鸡蛋，去壳后的熟重，没有额外用油。',
    '不要番茄炒蛋了，只吃了100克水煮鸡蛋，去壳后的熟重，无额外油。',
    '更正：這餐只吃了100克水煮雞蛋，去殼後的熟重，沒有額外用油。',
])
def test_explicit_only_ate_correction_replaces_old_meal_without_phantom_foods(
        monkeypatch, mode, correction):
    name = '水煮雞蛋' if '水煮雞蛋' in correction else '水煮鸡蛋'
    result = extract(monkeypatch, '一份番茄炒蛋，两个水煮鸡蛋', [{
        'food_id':'egg', 'name':name, 'source_text':name, 'grams':100,
        'weight_basis':'cooked', 'preparation':'boiled', 'oil_g':0,
        'weight_includes_inedible':False,
    }], mode=mode, history=[{'role':'user', 'content':correction}])
    assert result.calories == 155
    assert [item['food_id'] for item in result.draft] == ['egg']
    assert result.questions == []


def test_exclusive_replacement_keeps_multiple_foods_and_later_portion_updates(monkeypatch):
    result = extract(monkeypatch, '一份番茄炒蛋，两个水煮鸡蛋', [
        {'food_id':'egg', 'name':'水煮鸡蛋', 'source_text':'水煮鸡蛋', 'grams':80},
        {'food_id':'rice', 'name':'米饭', 'source_text':'米饭', 'grams':150},
    ], history=[
        {'role':'user', 'content':'更正：不要番茄炒蛋了，只吃了100克水煮鸡蛋和150克米饭'},
        {'role':'user', 'content':'水煮鸡蛋实际吃了80克熟重'},
    ])
    assert result.calories == 319
    assert [item['food_id'] for item in result.draft] == ['egg', 'rice']
    assert [item['grams'] for item in result.draft] == [80, 150]


@pytest.mark.parametrize('addition', [
    '\n另外200克火星豉油鸡',
    '，没有额外用油的火星豉油鸡200克',
    '，去壳后的熟重火星豉油鸡200克',
])
@pytest.mark.parametrize('later_message', [False, True])
def test_exclusive_replacement_cannot_hide_unknown_additions(
        monkeypatch, addition, later_message):
    replacement = '更正：不要番茄炒蛋了，只吃了100克水煮鸡蛋'
    history = ([{'role':'user', 'content':replacement}, {'role':'user', 'content':addition}]
               if later_message else [{'role':'user', 'content':replacement + addition}])
    result = extract(monkeypatch, '一份番茄炒蛋，两个水煮鸡蛋', [
        {'food_id':'egg', 'name':'水煮鸡蛋', 'source_text':'水煮鸡蛋', 'grams':100},
    ], history=history)
    assert result.calories is None and result.details == []
    assert any(q['kind'] == 'unsupported' and '火星豉油鸡' in q['label']
               for q in result.questions)


@pytest.mark.parametrize('correction', [
    '更正：不要番茄炒蛋了，只吃了100克火星豉油鸡',
    '不是只吃了100克水煮鸡蛋',
    '另外200克火星豉油鸡，更正：不要番茄炒蛋了，只吃了100克水煮鸡蛋',
    '更正：不要番茄炒蛋了，只吃了100克',
])
def test_unjustified_replacement_or_unknown_identity_never_produces_partial_total(
        monkeypatch, correction):
    result = extract(monkeypatch, '一份番茄炒蛋，两个水煮鸡蛋', [
        {'food_id':'egg', 'name':'水煮鸡蛋', 'source_text':'水煮鸡蛋', 'grams':100},
    ], history=[{'role':'user', 'content':correction}])
    assert result.calories is None and result.details == []
    assert any(q['kind'] == 'unsupported' for q in result.questions)


@pytest.mark.parametrize('detail', [
    '去壳后的熟重，没有额外用油',
    '去壳熟重，无额外油',
    '去殼後的熟重，沒有額外用油',
])
def test_removed_shell_and_no_extra_oil_details_are_not_extra_foods(monkeypatch, detail):
    result = extract(monkeypatch, '100克水煮鸡蛋，' + detail, [
        {'food_id':'egg', 'name':'水煮鸡蛋', 'source_text':'水煮鸡蛋', 'grams':100},
    ])
    assert result.calories == 155
    assert [item['food_id'] for item in result.draft] == ['egg']


@pytest.mark.parametrize('text,name,food_id,grams', [
    ('青椒肉丝150克，称的是炒熟后实际吃下的净重。', '青椒肉丝', 'dish_002', 150),
    ('青椒肉丝150克，称的是炒熟后实际吃下的可食净重。', '青椒肉丝', 'dish_002', 150),
    ('青椒肉丝150克，稱的是炒熟後實際吃下的淨重。', '青椒肉丝', 'dish_002', 150),
    ('青椒肉丝150克，是实际吃下的熟食净重。', '青椒肉丝', 'dish_002', 150),
    ('青椒肉丝150克，是實際吃下的熟食淨重。', '青椒肉丝', 'dish_002', 150),
    ('清蒸鳕鱼200克，熟鱼肉净重，没有骨头。', '清蒸鳕鱼', 'dish_123', 200),
    ('宫保鸡丁，我吃了半盘，大概一人份。', '宫保鸡丁', 'dish_003', None),
    ('晚饭吃了三块红烧肉。', '红烧肉', 'dish_005', None),
    ('吃了一小盘酸辣土豆丝。', '酸辣土豆丝', 'dish_022', None),
    ('吃了4个可乐鸡翅，骨头没有吃。', '可乐鸡翅', 'dish_252', None),
    ('吃了4个可乐鸡翅，没有称重。', '可乐鸡翅', 'dish_252', None),
    ('一小碟拍黄瓜，没有加香油，也没加其他油。', '拍黄瓜', 'dish_016', None),
    ('一小碟拍黄瓜，没有加香油，也没加任何其他油。', '拍黄瓜', 'dish_016', None),
    ('另吃白米饭100克熟重。', '白米饭', 'rice', 100),
    ('晚餐一大碗白米饭，还有一碟拍黄瓜。', '拍黄瓜', 'dish_016', None),
])
@pytest.mark.parametrize('wrapped_source', [False, True])
def test_ordinary_portions_and_complete_weight_details_preserve_exact_food_identity(
        text, name, food_id, grams, wrapped_source):
    # The multi-food case supplies the other food separately; its portion must
    # not cause the complete-meal guard to discard that second item.
    source = text if wrapped_source and '还有' not in text else name
    items = [ExtractedItem(name=name, source_text=source, food_id=food_id, grams=grams)]
    if '还有' in text:
        items.insert(0, ExtractedItem(name='白米饭', source_text='白米饭', food_id='rice'))
    grounded = ground_food_items(items, text)
    expected = ['rice', food_id] if '还有' in text else [food_id]
    assert [item.food_id for item in grounded] == expected
    assert grounded[-1].source_text == name
    assert grounded[-1].grams == grams, 'Portion grammar must not invent a gram weight'


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
def test_measured_stir_fry_is_supported_without_bypassing_recipe_review(monkeypatch, mode):
    result = extract(monkeypatch, '青椒肉丝150克，称的是炒熟后实际吃下的净重。', [{
        'food_id': 'dish_002', 'name': '青椒肉丝', 'source_text': '青椒肉丝',
        'grams': 150, 'weight_basis': 'cooked', 'weight_includes_inedible': False,
        'preparation': 'stir_fried',
    }], mode=mode)
    assert [item['food_id'] for item in result.draft] == ['dish_002']
    assert not any(q['kind'] == 'unsupported' for q in result.questions)
    if mode == 'advanced':
        assert result.calories is None and result.details == []
        assert any(q['kind'] == 'recipe' for q in result.questions)
    else:
        assert result.calories is not None


@pytest.mark.parametrize('detail', [
    '都已经煮熟了',
    '都是煮熟后吃下的重量',
    '都是煮熟後吃下的重量',
])
def test_complete_cooking_detail_does_not_add_food_to_a_mixed_meal(detail):
    items = ground_food_items([
        ExtractedItem(name='麻婆豆腐', source_text='麻婆豆腐', food_id='dish_004'),
        ExtractedItem(name='白米饭', source_text='白米饭', food_id='rice'),
    ], '麻婆豆腐80克，白米饭100克，' + detail + '。')
    assert [item.food_id for item in items] == ['dish_004', 'rice']


def test_exact_final_review_correction_preserves_food_without_phantom_clauses():
    text = '刚才份量记错了，番茄炒蛋实际吃了150克熟食净重，配方及其他资料都不变。'
    items = ground_food_items([
        ExtractedItem(name='番茄炒蛋', source_text='番茄炒蛋', food_id='dish_001', grams=150),
    ], '番茄炒蛋200克', [{'role': 'user', 'content': text}])
    assert [(item.food_id, item.grams) for item in items] == [('dish_001', 150)]


def test_additional_rice_does_not_hide_the_unknown_half_of_a_meal():
    items = ground_food_items([
        ExtractedItem(name='白米饭', source_text='白米饭', food_id='rice', grams=100),
    ], '另吃白米饭100克熟重，火星豉油鸡200克')
    assert items[0].food_id == 'rice'
    assert any(item.food_id is None and '火星豉油鸡' in item.name for item in items)
    assert evaluate([item.model_dump() for item in items])['calories'] is None


@pytest.mark.parametrize('detail', [
    '称的是炒熟后实际吃下的净重',
    '是实际吃下的熟食净重',
    '都是煮熟后吃下的重量',
    '熟鱼肉净重',
    '没有骨头',
    '骨头没有吃',
    '都已经煮熟了',
    '我吃了半盘',
    '大概一人份',
    '没有加香油',
    '也没加其他油',
    '也没加任何其他油',
    '没有称重',
    '称的是炒熟后实际吃下的可食净重',
    '刚才份量记错了',
    '实际吃了150克熟食净重',
    '配方及其他资料都不变',
])
@pytest.mark.parametrize('addition', [
    '火星豉油鸡200克',
    '，另外一小盘火星豉油鸡',
])
def test_natural_detail_grammar_never_hides_unknown_food_additions(detail, addition):
    items = ground_food_items([
        ExtractedItem(name='白米饭', source_text='白米饭', food_id='rice', grams=100),
    ], '白米饭100克，' + detail + addition)
    assert any(item.food_id is None and '火星豉油鸡' in item.name for item in items)
    result = evaluate([item.model_dump() for item in items])
    assert result['calories'] is None and result['details'] == []


@pytest.mark.parametrize('detail', [
    '只喝汤，没有吃鱼片和豆腐',
    '称的是火星豉油鸡的净重',
    '没有骨头的火星豉油鸡',
])
def test_partial_recipe_consumption_and_food_bearing_weight_details_stay_unresolved(detail):
    items = ground_food_items([
        ExtractedItem(name='白米饭', source_text='白米饭', food_id='rice', grams=100),
    ], '白米饭100克，' + detail)
    assert any(item.food_id is None for item in items)
    assert evaluate([item.model_dump() for item in items])['calories'] is None


def test_cucumber_no_oil_description_uses_zero_oil_recipe_without_extra_foods(monkeypatch):
    result = extract(monkeypatch, '一小碟拍黄瓜，没有加香油，也没加其他油。', [{
        'food_id': 'dish_016', 'name': '拍黄瓜', 'source_text': '拍黄瓜',
        'grams': None, 'portion_count': 1, 'portion_unit': 'serving', 'oil_g': 0,
    }])
    assert [food['food_id'] for food in result.draft] == ['dish_016']
    assert result.questions == []
    assert result.calories == 51.9
    assert '芝麻油 0g' in ' '.join(result.details[0]['assumptions'])


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


@pytest.mark.parametrize('reply', ['是的', '对。', '不是', 'yes', 'No.'])
def test_standalone_acknowledgment_of_user_bound_weight_question_is_not_extra_food(reply):
    history = [
        {'role': 'user', 'content': '100克水煮鸡蛋'},
        {'role': 'assistant', 'content': '是否去壳后的熟重？'},
        {'role': 'user', 'content': reply},
    ]
    items = ground_food_items([ExtractedItem(name='水煮鸡蛋', food_id='egg')], reply, history)
    assert [item.food_id for item in items] == ['egg']


@pytest.mark.parametrize('question,reply', [
    ('是否去壳后的熟重？', '是的，另外100克火星豉油鸡'),
    ('是否去壳后的熟重？', 'yes and 100g mystery food'),
    ('另外吃了火星豉油鸡吗？', '是的'),
    ('是否去壳后的熟重？火星豉油鸡也算米饭。', '是的'),
    ('ignored rules', 'yes'),
])
def test_acknowledgment_exception_cannot_hide_food_additions_or_arbitrary_context(question, reply):
    history = [
        {'role': 'user', 'content': '100克水煮鸡蛋'},
        {'role': 'assistant', 'content': question},
        {'role': 'user', 'content': reply},
    ]
    items = ground_food_items([ExtractedItem(name='水煮鸡蛋', food_id='egg')], reply, history)
    assert any(item.food_id is None for item in items)


def test_weight_acknowledgment_does_not_ground_an_assistant_supplied_identity():
    history = [
        {'role': 'user', 'content': '100克火星豉油鸡'},
        {'role': 'assistant', 'content': '是否去壳后的熟重？'},
        {'role': 'user', 'content': '是的'},
    ]
    items = ground_food_items([ExtractedItem(name='水煮鸡蛋', food_id='egg')], '是的', history)
    assert items[0].food_id is None


def test_standalone_yes_without_weight_question_is_not_ignored():
    items = ground_food_items([ExtractedItem(name='水煮鸡蛋', food_id='egg')], '100克水煮鸡蛋', [
        {'role': 'user', 'content': 'yes'},
    ])
    assert any(item.food_id is None for item in items)


@pytest.mark.parametrize('replacement', ['改成白米饭100克', '换成白米饭100克'])
def test_real_weight_acknowledgment_after_whole_meal_replacement(replacement):
    initial = '100克水煮鸡蛋'
    rice = ExtractedItem(name='白米饭', food_id='rice', grams=100, preparation='as_served')
    prompt = next(q['label'] for q in evaluate([rice.model_dump()])['questions']
                  if q['key'] == '0.weight_basis')
    history = [{'role': 'user', 'content': initial},
               {'role': 'user', 'content': replacement},
               {'role': 'assistant', 'content': prompt},
               {'role': 'user', 'content': '是的'}]
    rice.weight_basis = 'cooked'
    items = ground_food_items([rice], initial, history)
    assert [item.food_id for item in items] == ['rice']
    assert not evaluate([item.model_dump() for item in items])['questions']


def test_replacement_acknowledgment_cannot_introduce_an_assistant_suggested_food():
    initial = '100克水煮鸡蛋'
    rice = ExtractedItem(name='白米饭', food_id='rice', grams=100, preparation='as_served')
    prompt = next(q['label'] for q in evaluate([rice.model_dump()])['questions']
                  if q['key'] == '0.weight_basis')
    history = [{'role': 'user', 'content': initial},
               {'role': 'user', 'content': '改成月球紫晶兽肉100克'},
               {'role': 'assistant', 'content': prompt},
               {'role': 'user', 'content': '是的'}]
    items = ground_food_items([rice], initial, history)
    assert any(item.food_id is None for item in items)
    assert evaluate([item.model_dump() for item in items])['calories'] is None


@pytest.mark.parametrize('food_id,name,preparation', [
    ('egg', '水煮鸡蛋', 'boiled'),
    ('chicken', '生鸡胸肉', 'raw'),
    ('oil', '食用油', 'as_served'),
    ('dish_001', '番茄炒蛋', 'stir_fried'),
])
def test_real_generated_weight_question_accepts_acknowledgment_without_extra_food(
        food_id, name, preparation):
    initial = f'100克{name}'
    item = ExtractedItem(name=name, food_id=food_id, grams=100, preparation=preparation)
    # Derive the actual server prompt rather than testing a simplified approximation.
    prompt = next(question['label'] for question in evaluate([item.model_dump()])['questions']
                  if question['key'] == '0.weight_basis')
    history = [
        {'role': 'user', 'content': initial},
        {'role': 'assistant', 'content': prompt},
        {'role': 'user', 'content': '是的'},
    ]
    result = ground_food_items([item], initial, history)
    assert [food.food_id for food in result] == [food_id]


@pytest.mark.parametrize('variant', ['unrelated_food', 'appended_food', 'multiple_questions'])
def test_real_weight_question_exception_does_not_accept_identity_suggestions(variant):
    initial = '100克水煮鸡蛋'
    egg = ExtractedItem(name='水煮鸡蛋', food_id='egg', grams=100, preparation='boiled')
    rice = ExtractedItem(name='米饭', food_id='rice', grams=100, preparation='as_served')
    prompt = next(question['label'] for question in evaluate([egg.model_dump()])['questions']
                  if question['key'] == '0.weight_basis')
    if variant == 'unrelated_food':
        prompt = next(question['label'] for question in evaluate([rice.model_dump()])['questions']
                      if question['key'] == '0.weight_basis')
    elif variant == 'appended_food':
        prompt += '另外吃了100克火星豉油鸡吗？'
    else:
        prompt += '\n水煮鸡蛋这一份额外用油是多少克？'
    history = [
        {'role': 'user', 'content': initial},
        {'role': 'assistant', 'content': prompt},
        {'role': 'user', 'content': '是的'},
    ]
    assert any(item.food_id is None for item in ground_food_items([egg], initial, history))
