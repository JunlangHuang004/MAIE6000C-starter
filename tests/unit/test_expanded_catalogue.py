"""Exercise every maintained dish through both estimation modes, without a model call."""
from copy import deepcopy
import json
import zipfile

import pytest

from scripts.import_usda import DATA, validate_catalogue
from services.common.meal_engine import (
    ExtractedItem, apply_answers, catalogue, evaluate_mode,
)

FOODS = catalogue()['foods']
RECIPES = [food for food in FOODS if food['kind'] == 'recipe']
BY_NAME = {food['name']: food for food in RECIPES}


def test_snapshot_matches_authoring_sources_and_has_unique_dishes():
    validate_catalogue(FOODS)
    assert len(RECIPES) == 250
    assert len(FOODS) - len(RECIPES) == 138
    assert RECIPES == json.loads((DATA / 'recipes.json').read_text())
    selection = json.loads((DATA / 'usda_selection.json').read_text())
    assert {f['fdc_id'] for f in selection} == {
        f['fdc_id'] for f in FOODS if f['kind'] == 'ingredient'}
    assert all(f['variant_policy'] == 'one_home_style_reference_per_dish' for f in RECIPES)


@pytest.mark.parametrize('food', RECIPES, ids=lambda food: food['id'])
def test_each_recipe_estimates_and_requires_advanced_approval(food):
    draft = [ExtractedItem(food_id=food['id'], name=food['name'],
                           grams=200, weight_basis='cooked').model_dump()]
    basic = evaluate_mode(draft, 'basic')
    assert not basic['questions']
    assert basic['calories'] > 0
    assert basic['draft'] == draft
    pending = evaluate_mode(draft, 'advanced')
    assert pending['calories'] is None
    assert [q['key'] for q in pending['questions']] == ['0.recipe']
    accepted = apply_answers(draft, {'0.recipe': pending['questions'][0]['recipe']})
    advanced = evaluate_mode(accepted, 'advanced')
    assert not advanced['questions']
    for nutrient in ('calories', 'protein_g', 'fat_g', 'carbs_g'):
        assert advanced[nutrient] == basic[nutrient]
    assert advanced['details'][0]['sources']


@pytest.mark.parametrize('field,value', [
    ('yield_g', 0), ('yield_g', float('nan')), ('yield_g', True),
    ('ingredients', {'missing_food': 100}),
    ('ingredients', {'dish_001': 100}), ('ingredients', {'oil': -10}),
    ('ingredients', {'oil': float('inf')}), ('ingredients', {'oil': 0}),
])
def test_import_rejects_invalid_recipe_before_snapshot_write(field, value):
    foods = deepcopy(FOODS)
    recipe = next(f for f in foods if f['kind'] == 'recipe')
    recipe['recipe'][field] = value
    with pytest.raises(ValueError):
        validate_catalogue(foods)


def test_import_rejects_ambiguous_alias_and_duplicate_id():
    foods = deepcopy(FOODS)
    recipes = [f for f in foods if f['kind'] == 'recipe']
    recipes[1]['aliases'].append(recipes[0]['name'])
    with pytest.raises(ValueError, match='alias'):
        validate_catalogue(foods)
    with pytest.raises(ValueError, match='IDs'):
        validate_catalogue(FOODS + [FOODS[0]])


@pytest.mark.parametrize('name,unit,count,grams', [
    ('白菜猪肉饺子', 'piece', 10, 200),
    ('白菜猪肉饺子', 'serving', 2, 400),
    ('鲜肉馄饨', 'piece', 6, 90),
    ('鲜肉馄饨', 'bowl', 1, 180),
    ('馒头', 'piece', 2, 120),
    ('煎荷包蛋', 'piece', 2, 90),
])
def test_piece_and_serving_defaults_are_distinct_visible_assumptions(name, unit, count, grams):
    draft = [ExtractedItem(food_id=BY_NAME[name]['id'], name=name,
                           portion_unit=unit, portion_count=count).model_dump()]
    result = evaluate_mode(draft, 'basic')
    assert result['details'][0]['grams'] == grams
    assert result['draft'][0]['grams'] is None
    assert '未提供克数' in ' '.join(result['details'][0]['assumptions'])
    assert evaluate_mode(result['draft'], 'advanced')['calories'] is None
    draft[0]['grams'] = 123
    assert evaluate_mode(draft, 'basic')['details'][0]['grams'] == 123


def test_expanded_recipe_oil_correction_changes_energy_without_retraining():
    food = BY_NAME['青椒牛肉']
    draft = [ExtractedItem(food_id=food['id'], name=food['name'],
                           grams=210, weight_basis='cooked').model_dump()]
    recipe = deepcopy(food['recipe'])
    accepted = apply_answers(draft, {'0.recipe': recipe})
    before = evaluate_mode(accepted, 'advanced')
    accepted[0]['recipe']['ingredients']['oil'] += 10
    after = evaluate_mode(accepted, 'advanced')
    # Half of a 420g batch consumes 5g extra oil at USDA's 884 kcal/100g.
    assert after['calories'] - before['calories'] == pytest.approx(44.2, abs=0.1)
    assert 'beef_lean' in recipe['ingredients'] and 'beef' not in recipe['ingredients']


def test_import_rejects_invalid_piece_weight():
    foods = deepcopy(FOODS)
    next(f for f in foods if f['kind'] == 'recipe')['portion_weights_g'] = {'piece': 0}
    with pytest.raises(ValueError, match='portions'):
        validate_catalogue(foods)


@pytest.mark.parametrize('bad_input', ['missing_nutrient', 'duplicate_alias', 'duplicate_fdc'])
def test_failed_import_preserves_previous_snapshot(tmp_path, monkeypatch, bad_input):
    from scripts import import_usda as importer
    selection = [{'id':'oil', 'name':'oil', 'fdc_id':1, 'state':'as_sold', 'aliases':['oil']}]
    if bad_input == 'duplicate_fdc':
        selection.append(dict(selection[0], id='oil_duplicate'))
    (tmp_path/'usda_selection.json').write_text(json.dumps(selection))
    recipe = dict(id='dish_a', name='A', aliases=['A'], kind='recipe',
                  recipe={'ingredients':{'oil':10}, 'yield_g':10})
    recipes = [recipe]
    if bad_input == 'duplicate_alias':
        recipes.append(dict(recipe, id='dish_b'))
    (tmp_path/'recipes.json').write_text(json.dumps(recipes))
    previous = '{"version":"previous","foods":[]}'
    (tmp_path/'catalogue.json').write_text(previous)
    archive_path = tmp_path/'source.zip'
    nutrients = 'fdc_id,nutrient_id,amount\n1,1008,884\n1,1004,100\n1,1003,0\n'
    if bad_input != 'missing_nutrient':
        nutrients += '1,1005,0\n'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr('food.csv', 'fdc_id,description\n1,Test oil\n')
        archive.writestr('food_nutrient.csv', nutrients)
    monkeypatch.setattr(importer, 'DATA', tmp_path)
    with pytest.raises(ValueError):
        importer.build(archive_path)
    assert (tmp_path/'catalogue.json').read_text() == previous


@pytest.mark.parametrize('name', [
    '糖醋里脊', '青椒牛肉', '白切鸡', '糖醋鱼', '清蒸南瓜',
    '虾仁蒸蛋', '香菇鸡汤', '白菜猪肉饺子',
])
def test_portion_and_yield_scaling_preserve_recipe_energy(name):
    food = BY_NAME[name]
    draft = [ExtractedItem(food_id=food['id'], name=name, grams=100).model_dump()]
    first = evaluate_mode(draft, 'basic')
    draft[0]['grams'] = 200
    doubled = evaluate_mode(draft, 'basic')
    for key in ('calories', 'protein_g', 'fat_g', 'carbs_g'):
        assert doubled[key] == pytest.approx(2*first[key], abs=0.11)
    draft[0]['recipe_yield_g'] = 2*food['recipe']['yield_g']
    diluted = evaluate_mode(draft, 'basic')
    for key in ('calories', 'protein_g', 'fat_g', 'carbs_g'):
        assert diluted[key] == first[key]


def test_advanced_bone_weight_requires_actual_edible_grams():
    mode = 'advanced'
    food = BY_NAME['糖醋排骨']
    draft = [ExtractedItem(food_id=food['id'], name=food['name'], grams=300,
                           weight_basis='cooked', weight_includes_inedible=True).model_dump()]
    pending = evaluate_mode(draft, mode)
    assert pending['calories'] is None and pending['details'] == []
    assert [q['key'] for q in pending['questions']] == ['0.grams']
    assert pending['draft'][0]['grams'] == 300
    answered = apply_answers(draft, {'0.grams':180}, mode)
    assert answered[0]['weight_includes_inedible'] is False
    result = evaluate_mode(answered, mode)
    assert result['calories'] is None
    assert result['questions'][0]['key'] == '0.recipe'
    assert draft[0]['weight_includes_inedible'] is True


def test_basic_bone_weight_uses_labelled_rough_estimate_and_preserves_gross_fact():
    food = BY_NAME['糖醋排骨']
    draft = [ExtractedItem(food_id=food['id'], name=food['name'], grams=300,
                           weight_basis='cooked', weight_includes_inedible=True).model_dump()]
    result = evaluate_mode(draft, 'basic')
    assert result['calories'] > 0 and not result['questions']
    assert result['details'][0]['grams'] == 180
    assert '60%' in ' '.join(result['details'][0]['assumptions'])
    assert result['draft'] == draft
    advanced = evaluate_mode(result['draft'], 'advanced')
    assert advanced['calories'] is None
    assert advanced['questions'][0]['key'] == '0.grams'


def test_explicit_recipe_corrections_prefill_without_automatic_approval():
    food = BY_NAME['宫保鸡丁']
    draft = [ExtractedItem(food_id=food['id'], name=food['name'], grams=200,
                           weight_basis='cooked', recipe_yield_g=400,
                           recipe_ingredients={'peanut':0, 'oil':5}).model_dump()]
    result = evaluate_mode(draft, 'advanced')
    recipe = result['questions'][0]['recipe']
    assert recipe['ingredients']['peanut'] == 0
    assert recipe['ingredients']['oil'] == 5
    assert recipe['yield_g'] == 400
    assert result['calories'] is None
    basic = evaluate_mode(draft, 'basic')
    reference = evaluate_mode([ExtractedItem(
        food_id=food['id'], name=food['name'], grams=200).model_dump()], 'basic')
    assert basic['calories'] < reference['calories']
