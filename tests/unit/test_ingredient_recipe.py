"""Independent arithmetic and trust-boundary checks for explicit user recipes."""
from copy import deepcopy

import pytest

from services.common.ingredient_recipe import recipe_detail, validate_ingredient_recipe
from services.common.meal_engine import KEYS, ExtractedItem, catalogue, evaluate_mode


def recipe(basis='consumed'):
    multiplier = 2 if basis == 'batch' else 1
    return {
        'name': 'My chicken recipe', 'basis': basis, 'accepted': True,
        'ingredients': [
            {'food_id': 'chicken', 'grams': 150 * multiplier},
            {'food_id': 'oil', 'grams': 5 * multiplier},
            {'food_id': 'soy_sauce', 'grams': 10 * multiplier},
        ],
        'batch_yield_g': 600 if basis == 'batch' else None,
        'consumed_g': 150 if basis == 'batch' else None,
    }


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
@pytest.mark.parametrize('basis,expected_calories,expected_grams,factor', [
    ('consumed', 229.5, 165, 1),
    ('batch', 114.75, 150, 0.25),
])
def test_recipe_uses_catalogue_nutrients_and_correct_consumed_fraction(
        mode, basis, expected_calories, expected_grams, factor):
    value = recipe(basis)
    original = deepcopy(value)
    foods = {food['id']: food for food in catalogue()['foods']}
    totals, detail = recipe_detail(value, foods, KEYS)
    # Independent calculation: chicken 120, oil 884, soy sauce 53 kcal / 100 g.
    assert totals['calories'] == pytest.approx(expected_calories)
    portion_scale = 0.5 if basis == 'batch' else 1
    assert totals['protein_g'] == pytest.approx(34.564 * portion_scale)
    assert totals['fat_g'] == pytest.approx(8.987 * portion_scale)
    assert totals['carbs_g'] == pytest.approx(0.493 * portion_scale)
    assert detail['grams'] == expected_grams
    assert detail['food_id'] is None
    assert detail['kind'] == 'custom_recipe'
    assert len(detail['sources']) == 3
    provenance = detail['quantity_provenance']
    assert provenance['factor'] == factor
    assert provenance['basis'] == basis
    assert [row['state'] for row in provenance['ingredients']] == ['raw', 'as_sold', 'as_sold']
    assert provenance['ingredients'][0]['consumed_grams'] == (75 if basis == 'batch' else 150)
    result = evaluate_mode([{'name': value['name'], 'custom_recipe': value}], mode)
    assert result['questions'] == []
    assert result['calories'] == round(expected_calories, 1)
    assert result['draft'][0]['custom_recipe'] == original
    assert value == original, 'Calculation must not overwrite explicitly supplied quantities'


@pytest.mark.parametrize('bad_grams', [0, -1, 10001, True, '150', float('nan'), float('inf')])
def test_invalid_ingredient_weights_never_reach_arithmetic(bad_grams):
    value = recipe()
    value['ingredients'][0]['grams'] = bad_grams
    with pytest.raises(ValueError):
        evaluate_mode([{'name': 'User recipe', 'custom_recipe': value}], 'basic')


@pytest.mark.parametrize('patch', [
    {'ingredients': [{'food_id': 'missing_food', 'grams': 100}]},
    {'ingredients': [{'food_id': 'dish_001', 'grams': 100}]},
    {'ingredients': [{'food_id': 'chicken', 'grams': 100}, {'food_id': 'chicken', 'grams': 50}]},
    {'ingredients': []},
    {'ingredients': [{'food_id': 'chicken', 'grams': 100, 'calories': 1}]},
    {'accepted': False},
    {'accepted': 'true'},
    {'calories': 1},
    {'name': '   '},
    {'name': 'x' * 121},
    {'basis': 'batch'},
    {'basis': 'batch', 'batch_yield_g': 100, 'consumed_g': 101},
    {'basis': 'batch', 'batch_yield_g': 0, 'consumed_g': 1},
    {'basis': 'consumed', 'batch_yield_g': 100, 'consumed_g': 50},
])
def test_recipe_requires_reviewed_identity_complete_portions_and_no_client_nutrients(patch):
    value = {**recipe(), **patch}
    with pytest.raises(ValueError):
        validate_ingredient_recipe(value, {food['id']: food for food in catalogue()['foods']})


def test_qwen_cannot_create_trusted_custom_recipe_metadata():
    with pytest.raises(ValueError):
        ExtractedItem.model_validate({'name': 'Unknown dish', 'custom_recipe': recipe()})


def test_recipe_row_limit_rejects_an_overlong_list_of_valid_distinct_ingredients():
    foods = {food['id']: food for food in catalogue()['foods']}
    rows = [{'food_id': fid, 'grams': 10} for fid, food in foods.items()
            if food['kind'] == 'ingredient'][:31]
    assert len(rows) == 31
    with pytest.raises(ValueError):
        validate_ingredient_recipe({**recipe(), 'ingredients': rows}, foods)


@pytest.mark.parametrize('facts,kind', [
    ({'grams': 100}, 'user_grams'),
    ({'portion_count': 2, 'portion_unit': 'bowl'}, 'portion_reference'),
    ({}, 'default_portion'),
    ({'grams': 100, 'weight_includes_inedible': True}, 'edible_fraction'),
])
def test_basic_quantity_evidence_distinguishes_facts_from_assumptions(facts, kind):
    draft = [ExtractedItem(name='米饭', food_id='rice', **facts).model_dump()]
    before = deepcopy(draft)
    result = evaluate_mode(draft, 'basic')
    assert result['questions'] == []
    provenance = result['details'][0]['quantity_provenance']
    assert provenance['kind'] == kind
    assert provenance['input_grams'] == facts.get('grams')
    assert provenance['calculated_grams'] == result['details'][0]['grams']
    if kind == 'edible_fraction':
        assert provenance['calculated_grams'] == 60
        assert provenance['edible_fraction'] == 0.6
    elif kind == 'portion_reference':
        assert provenance['portion_count'] == 2
        assert provenance['reference_grams'] * 2 == provenance['calculated_grams']
    assert result['draft'] == before
    assert draft == before


def test_custom_recipe_does_not_hide_another_unresolved_food():
    draft = [
        {'name': 'User recipe', 'custom_recipe': recipe()},
        ExtractedItem(name='Still unsupported').model_dump(),
    ]
    result = evaluate_mode(draft, 'basic')
    assert len(result['questions']) == 1
    assert result['questions'][0]['key'] == '1.food_id'
    assert all(result[key] is None for key in KEYS)
    assert result['details'] == []
