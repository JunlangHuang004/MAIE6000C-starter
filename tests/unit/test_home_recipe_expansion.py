"""Keep the menu expansion traceable, source-backed and conservative about identity."""
import hashlib
import json
import math

import pytest

from services.common.food_matching import ground_food_items, name_index
from services.common.meal_engine import ExtractedItem, catalogue, evaluate_mode


FOODS = catalogue()['foods']
BY_ID = {food['id']: food for food in FOODS}
NEW_IDS = {f'dish_{number}' for number in range(351, 386)} - {'dish_373'}
NEW_RECIPES = [food for food in FOODS if food['id'] in NEW_IDS]


def fingerprint(value):
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode()).hexdigest()


def test_expansion_preserves_original_data_except_documented_white_chicken_correction():
    ingredients = [food for food in FOODS if food['kind'] == 'ingredient'
                   and food['id'] not in {'chicken_skin_stewed', 'chicken_meat_stewed'}]
    assert fingerprint(ingredients) == (
        '23a20d4f62d090b53d83dff33e1d63aa51c791263d25c9c5ad7bbc4a3298330d')
    originals = [{key: value for key, value in food.items() if key != 'aliases'}
                 for food in FOODS
                 if food['id'].startswith('dish_') and int(food['id'][5:]) <= 350
                 and food['id'] != 'dish_109']
    assert fingerprint(originals) == (
        '0a27d66f8a03bcd0ce645c130eed788cb7fa3d41f9b0ad5afd4c7993a79f4018')
    assert {food['id'] for food in NEW_RECIPES} == NEW_IDS


@pytest.mark.parametrize('food', NEW_RECIPES, ids=lambda food: food['id'])
def test_new_reference_has_separate_discovery_and_nutrient_provenance(food):
    source = food['source']
    assert source['license'] == 'Project-authored'
    assert source['quantity_origin'] == 'project_authored_assumptions'
    assert source['discovery_scope'] == (
        'dish_names_and_style_only_not_recipe_quantities_or_nutrients')
    assert 'https://home.meishichina.com/recipe-menu.html' in source['discovery_urls']
    assert all(url.startswith('https://home.meishichina.com/')
               for url in source['discovery_urls'])
    assert 'nutrients' not in food, 'Dish macros must be computed from the editable batch'
    assert food['nutrition_basis'] == 'recipe_batch_then_cooked_weight'
    for ingredient_id in food['recipe']['ingredients']:
        ingredient = BY_ID[ingredient_id]
        assert ingredient['kind'] == 'ingredient'
        assert ingredient['source']['license'] == 'CC0-1.0'
        assert ingredient['source']['id'] == str(ingredient['fdc_id'])


@pytest.mark.parametrize('food', NEW_RECIPES, ids=lambda food: food['id'])
def test_new_dish_name_grounds_and_per_100g_estimate_is_editable_recipe_arithmetic(food):
    item = ExtractedItem(name=food['name'], source_text=food['name'],
                         food_id='dish_010', grams=100, weight_basis='cooked')
    grounded = ground_food_items([item], '100克' + food['name'])
    assert [result.food_id for result in grounded] == [food['id']]
    draft = [item.model_dump()]
    result = evaluate_mode(draft, 'basic')
    assert not result['questions']
    assert result['draft'] == draft
    expected = {}
    for key in ('calories', 'protein_g', 'fat_g', 'carbs_g'):
        expected[key] = sum(BY_ID[ingredient]['nutrients'][key] * grams / 100
                            for ingredient, grams in food['recipe']['ingredients'].items())
        expected[key] *= 100 / food['recipe']['yield_g']
        assert math.isfinite(expected[key]) and expected[key] >= 0
        assert result[key] == round(expected[key], 1)
    assert 0 < expected['calories'] < 700
    assert sum(expected[key] for key in ('protein_g', 'fat_g', 'carbs_g')) <= 100
    pending = evaluate_mode(draft, 'advanced')
    assert pending['calories'] is None
    assert [question['kind'] for question in pending['questions']] == ['recipe']


@pytest.mark.parametrize('alias,food_id', [
    ('肉饼蒸蛋', 'dish_015'), ('蒜蓉西兰花', 'dish_017'),
    ('凉拌黑木耳', 'dish_166'), ('牛肉炖土豆', 'dish_008'),
    ('糖醋鲤鱼', 'dish_122'), ('蒜泥茄子', 'dish_153'),
    ('青椒炒鸡蛋', 'dish_031'), ('菠菜鸡蛋汤', 'dish_213'),
    ('青椒炒肉丝', 'dish_002'), ('炒莴笋', 'dish_301'),
])
def test_reviewed_menu_synonyms_reuse_existing_ids(alias, food_id):
    assert name_index()[alias] == {food_id}
    assert sum(alias == food['name'] for food in NEW_RECIPES) == 0


@pytest.mark.parametrize('name', [
    '三杯鸡', '皮蛋瘦肉粥', '酸菜鱼', '梅菜扣肉', '芹菜炒香干',
    '韭菜炒香干', '韭菜盒子', '手撕杏鲍菇', '肉末酸豆角', '白灼菜心',
    '紫菜蛋花汤', '蒜薹炒肉', '老醋花生', '阳春面', '啤酒鸭', '盐水鸭',
])
def test_missing_essential_ingredients_remain_unresolved(name):
    assert name not in name_index()
    item = ExtractedItem(name=name, source_text=name, food_id='dish_001', grams=100)
    result = ground_food_items([item], '100克' + name)
    assert result[0].food_id is None
    assert evaluate_mode([food.model_dump() for food in result], 'basic')['calories'] is None


def test_unpublished_salt_duck_reference_is_deferred_without_reusing_its_id():
    assert 'dish_373' not in BY_ID
    assert len(NEW_RECIPES) == 34
    assert BY_ID['dish_372']['name'] == '盐焗鸡'
    assert BY_ID['dish_374']['name'] == '棒棒鸡'


def test_distinct_sesame_chicken_and_potato_preparations_have_distinct_formulas():
    assert 'sesame_paste' not in BY_ID['dish_255']['recipe']['ingredients']
    bang_bang = next(food for food in NEW_RECIPES if food['name'] == '棒棒鸡')
    assert bang_bang['recipe']['ingredients']['sesame_paste'] > 0
    pepper_potato = next(food for food in NEW_RECIPES if food['name'] == '青椒土豆丝')
    assert 'vinegar' not in pepper_potato['recipe']['ingredients']
    assert BY_ID['dish_022']['recipe']['ingredients']['vinegar'] > 0
