"""Prevent raw-fat retention and unreported dipping oil in the cooked reference."""
from copy import deepcopy

from services.common.ingredient_recipe import recipe_detail
from services.common.meal_engine import ExtractedItem, catalogue, evaluate_mode


FOODS = {food['id']: food for food in catalogue()['foods']}


def test_cooked_chicken_records_preserve_official_state_and_source_values():
    for food_id, fdc_id, energy, protein, fat in [
        ('chicken_skin_stewed', 171051, 219, 24.68, 12.56),
        ('chicken_meat_stewed', 171451, 177, 27.29, 6.71),
    ]:
        food = FOODS[food_id]
        assert food['state'] == 'cooked'
        assert food['fdc_id'] == fdc_id
        assert food['nutrients'] == {
            'calories': energy, 'protein_g': protein, 'fat_g': fat, 'carbs_g': 0}
        assert 'cooked, stewed' in food['source']['description']
    assert FOODS['chicken_skin']['state'] == 'raw'
    assert FOODS['chicken_skin']['nutrients']['calories'] == 215


def test_white_chicken_uses_cooked_proxy_and_excludes_unreported_sauce():
    food = FOODS['dish_109']
    assert food['source']['reference_scope'] == (
        'cooked_chicken_proxy_not_measured_white_cut_chicken')
    assert '不是白切鸡实测值' in food['method']
    assert '默认不含蘸汁' in food['method']
    recipe = food['recipe']
    assert 'chicken_skin' not in recipe['ingredients']
    assert recipe['ingredients']['oil'] == 0
    assert recipe['yield_g'] == recipe['ingredients']['chicken_skin_stewed']
    draft = [ExtractedItem(food_id='dish_109', name='白切鸡', grams=200,
                           weight_basis='cooked').model_dump()]
    basic = evaluate_mode(draft, 'basic')
    assert basic['calories'] == 438
    assert basic['fat_g'] == 25.1
    assert basic['protein_g'] == 49.4
    assert basic['details'][0]['sources'][0]['id'] == '171051'
    assert evaluate_mode(draft, 'advanced')['calories'] is None


def test_explicit_skinless_meat_and_oil_keep_separate_measured_amounts():
    recipe = dict(name='白切鸡去皮实际食材', basis='consumed', accepted=True,
                  ingredients=[dict(food_id='chicken_meat_stewed', grams=200)])
    keys = ('calories', 'protein_g', 'fat_g', 'carbs_g')
    before, _ = recipe_detail(recipe, FOODS, keys)
    assert before['calories'] == 354
    with_oil = deepcopy(recipe)
    with_oil['ingredients'].append(dict(food_id='oil', grams=5))
    after, _ = recipe_detail(with_oil, FOODS, keys)
    assert round(after['calories'] - before['calories'], 1) == 44.2
    assert after['protein_g'] == before['protein_g']
