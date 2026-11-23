"""Keep CFS prepared-dish evidence separate from editable ingredient arithmetic."""
from copy import deepcopy

import pytest

from services.common import meal_engine
from services.common.meal_engine import ExtractedItem, apply_answers, catalogue, evaluate_mode
from services.common.schemas import NutritionAnalysisResponse


KEYS = ('calories', 'protein_g', 'fat_g', 'carbs_g')
FOODS = {food['id']: food for food in catalogue()['foods']}
REFERENCES = [food for food in FOODS.values() if food.get('measured_reference')]


def draft_for(food, **changes):
    return [ExtractedItem(food_id=food['id'], name=food['name'], grams=100,
                          weight_basis='cooked', **changes).model_dump()]


def recipe_totals(recipe, grams):
    return {key: round(sum(FOODS[food_id]['nutrients'][key] * weight / 100
                          for food_id, weight in recipe['ingredients'].items())
                       * grams / recipe['yield_g'], 1) for key in KEYS}


def test_targeted_measured_coverage_and_large_discrepancy_values():
    assert {food['id'] for food in REFERENCES} == {
        'dish_012', 'dish_266', 'dish_341', 'dish_004', 'dish_007',
        'dish_064', 'dish_110', 'dish_202', 'dish_269', 'dish_339',
    }
    for food_id, calories in [('dish_012', 230), ('dish_266', 240), ('dish_341', 190)]:
        result = evaluate_mode(draft_for(FOODS[food_id]), 'basic')
        assert result['calories'] == calories


@pytest.mark.parametrize('food', REFERENCES, ids=lambda food: food['id'])
def test_complete_source_vector_scales_and_is_snapshotted(food):
    reference = food['measured_reference']
    draft = draft_for(food)
    first = evaluate_mode(draft, 'basic')
    assert not first['questions'] and first['draft'] == draft
    assert draft[0].get('calculation_basis') is None
    for key in KEYS:
        assert first[key] == round(reference['nutrients'][key], 1)
    detail = first['details'][0]
    assert detail['calculation_basis'] == 'measured_reference'
    assert detail['carbohydrate_basis'] == 'available'
    assert detail['measured_reference'] == reference
    assert detail['measured_reference'] is not reference
    assert detail['sources'] == [reference['source']]
    assert detail['sources'][0] is not reference['source']
    assert detail['calculation_evidence']['reference_version'] == reference['version']
    assert 'recipe' not in detail['calculation_evidence']
    assert NutritionAnalysisResponse.model_validate(
        first).carbohydrate_summary['basis'] == 'available'
    draft[0]['grams'] = 200
    doubled = evaluate_mode(draft, 'basic')
    for key in KEYS:
        assert doubled[key] == round(reference['nutrients'][key] * 2, 1)
    NutritionAnalysisResponse.model_validate(doubled)


@pytest.mark.parametrize('food', REFERENCES, ids=lambda food: food['id'])
def test_advanced_explicit_choice_precedes_formula_review(food):
    draft = draft_for(food)
    pending = evaluate_mode(draft, 'advanced')
    assert [q['key'] for q in pending['questions']] == ['0.calculation_basis']
    assert pending['calories'] is None
    with pytest.raises(ValueError):
        apply_answers(draft, {'0.recipe': food['recipe']})
    selected = apply_answers(draft, {'0.calculation_basis': 'measured_reference'})
    measured = evaluate_mode(selected, 'advanced')
    assert not measured['questions']
    assert measured['calories'] == food['measured_reference']['nutrients']['calories']
    selected = apply_answers(draft, {'0.calculation_basis': 'ingredient_recipe'})
    review = evaluate_mode(selected, 'advanced')
    assert [q['key'] for q in review['questions']] == ['0.recipe']
    accepted = apply_answers(selected, {'0.recipe': review['questions'][0]['recipe']})
    calculated = evaluate_mode(accepted, 'advanced')
    assert {key: calculated[key] for key in KEYS} == recipe_totals(food['recipe'], 100)
    assert calculated['details'][0]['calculation_basis'] == 'ingredient_recipe'
    assert calculated['details'][0]['calculation_evidence']['method'] == food['method']


@pytest.mark.parametrize('correction', [
    {'oil_g': 0}, {'oil_g': 5}, {'recipe_ingredients': {'sugar': 0}},
    {'recipe_yield_g': 1000}, {'recipe_confirmed': True},
])
def test_explicit_quantities_override_even_a_previous_measured_choice(correction):
    food = FOODS['dish_266']
    draft = draft_for(food)
    draft[0].update(calculation_basis='measured_reference', **correction)
    result = evaluate_mode(draft, 'basic')
    detail = result['details'][0]
    assert detail['calculation_basis'] == 'ingredient_recipe'
    assert 'measured_reference' not in detail
    assert detail['carbohydrate_basis'] == 'total_by_difference'
    recipe = detail['calculation_evidence']['recipe']
    assert {key: result[key] for key in KEYS} == recipe_totals(recipe, 100)
    if not correction.get('recipe_confirmed'):
        pending = evaluate_mode(draft, 'advanced')
        assert [q['key'] for q in pending['questions']] == ['0.recipe']


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
@pytest.mark.parametrize('changes,key', [
    ({'weight_basis': 'raw'}, '0.weight_basis'),
    ({'weight_basis': 'as_sold'}, '0.weight_basis'),
    ({'weight_includes_inedible': True}, '0.grams'),
    ({'uncertainty': '实际做法不同，需要核对'}, '0.resolved'),
])
def test_reference_does_not_convert_known_weight_mismatch_or_uncertain_identity(mode, changes, key):
    draft = draft_for(FOODS['dish_012'])
    draft[0].update(calculation_basis='measured_reference', **changes)
    result = evaluate_mode(draft, mode)
    assert key in {question['key'] for question in result['questions']}
    assert result['details'] == [] and all(result[key] is None for key in KEYS)
    assert result['draft'] == draft


def test_basic_reference_portions_remain_assumptions_and_advanced_requires_weight():
    food = FOODS['dish_266']
    draft = [ExtractedItem(food_id=food['id'], name=food['name']).model_dump()]
    basic = evaluate_mode(draft, 'basic')
    detail = basic['details'][0]
    assert detail['calculation_basis'] == 'measured_reference'
    assert detail['quantity_provenance']['kind'] == 'default_portion'
    assert detail['quantity_provenance']['input_grams'] is None
    assert detail['grams'] == food['default_portion_g']
    assert basic['draft'] == draft
    assert '未说明重量状态' in ' '.join(detail['assumptions'])
    pending = evaluate_mode(basic['draft'], 'advanced')
    assert {q['key'] for q in pending['questions']} == {
        '0.calculation_basis', '0.grams', '0.weight_basis'}
    draft[0].update(portion_count=2, portion_unit='piece')
    pending = evaluate_mode(draft, 'basic')
    assert [q['key'] for q in pending['questions']] == ['0.grams']


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
@pytest.mark.parametrize('preparation', ['raw', 'boiled', 'steamed', 'other'])
def test_shrimp_egg_reference_requires_source_compatible_preparation(mode, preparation):
    draft = draft_for(FOODS['dish_012'], preparation=preparation)
    if mode == 'advanced':
        draft = apply_answers(draft, {'0.calculation_basis': 'measured_reference'}, mode)
    pending = evaluate_mode(draft, mode)
    assert pending['details'] == [] and all(pending[key] is None for key in KEYS)
    assert [q['key'] for q in pending['questions']] == ['0.preparation']
    assert {option['value'] for option in pending['questions'][0]['options']} == {
        'as_served', 'stir_fried'}
    with pytest.raises(ValueError):
        apply_answers(draft, {'0.preparation': 'boiled'}, mode)
    accepted = apply_answers(draft, {'0.preparation': 'stir_fried'}, mode)
    assert evaluate_mode(accepted, mode)['calories'] == 230


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
def test_compatibility_uses_source_description_not_the_editable_recipe_method(mode):
    # CFS describes this record as steamed; the illustrative template is boiled.
    food = FOODS['dish_110']
    draft = draft_for(food, preparation='steamed')
    if mode == 'advanced':
        draft = apply_answers(draft, {'0.calculation_basis': 'measured_reference'}, mode)
    result = evaluate_mode(draft, mode)
    assert not result['questions']
    assert result['calories'] == food['measured_reference']['nutrients']['calories']
    draft[0]['preparation'] = 'boiled'
    assert evaluate_mode(draft, mode)['calories'] is None


def test_source_unspecified_cooking_route_accepts_only_source_state_and_keeps_edits_separate():
    food = FOODS['dish_266']
    assert food['measured_reference']['compatible_preparations'] == ['as_served']
    draft = draft_for(food, preparation='fried')
    pending = evaluate_mode(draft, 'basic')
    assert [q['key'] for q in pending['questions']] == ['0.preparation']
    draft[0]['preparation'] = None
    result = evaluate_mode(draft, 'basic')
    assert result['calories'] == 240
    assert '未说明做法' in ' '.join(result['details'][0]['assumptions'])
    draft[0].update(preparation='fried', oil_g=0)
    calculated = evaluate_mode(draft, 'basic')
    assert not calculated['questions']
    assert calculated['details'][0]['calculation_basis'] == 'ingredient_recipe'


def test_custom_and_accepted_similar_recipe_do_not_inherit_measured_dish_nutrients():
    food = FOODS['dish_266']
    recipe = {
        'name': '用户实际配方', 'basis': 'batch', 'accepted': True,
        'ingredients': [{'food_id': food_id, 'grams': grams}
                        for food_id, grams in food['recipe']['ingredients'].items() if grams > 0],
        'batch_yield_g': food['recipe']['yield_g'], 'consumed_g': 100,
    }
    draft = [{'name': recipe['name'], 'custom_recipe': recipe}]
    result = evaluate_mode(draft, 'basic')
    assert {key: result[key] for key in KEYS} == recipe_totals(food['recipe'], 100)
    draft[0]['reference_selection'] = {
        'acknowledged': True, 'source_food_id': food['id'], 'source_name': food['name'],
        'original_name': '未知家常菜',
    }
    similar = evaluate_mode(draft, 'advanced')
    assert {key: similar[key] for key in KEYS} == recipe_totals(food['recipe'], 100)
    assert similar['details'][0]['approximate_reference'] is True
    assert similar['details'][0]['calculation_basis'] == 'custom_recipe'
    assert 'measured_reference' not in similar['details'][0]


def mixed_result():
    draft = draft_for(FOODS['dish_266'])
    draft.append(ExtractedItem(food_id='rice', name='白米饭', grams=100).model_dump())
    return evaluate_mode(draft, 'basic')


def test_mixed_carbohydrate_definitions_have_separate_durable_subtotals():
    result = mixed_result()
    assert result['questions'] == [] and result['carbs_g'] is None
    assert result['calories'] == 370
    expected_summary = {
        'basis': 'mixed',
        'available_g': round(FOODS['dish_266']['measured_reference']['nutrients']['carbs_g'], 1),
        'total_by_difference_g': 28.2,
    }
    validated = NutritionAnalysisResponse.model_validate(result)
    assert validated.model_dump()['carbohydrate_summary'] == expected_summary
    # The AI HTTP response includes the computed field; the worker validates that
    # wire representation again, deriving rather than trusting the supplied summary.
    wire = validated.model_dump()
    wire['carbohydrate_summary'] = {'basis': 'available', 'available_g': 9999}
    assert NutritionAnalysisResponse.model_validate(wire).carbohydrate_summary == expected_summary
    another = draft_for(FOODS['dish_012']) + draft_for(FOODS['dish_266'])
    homogeneous = evaluate_mode(another, 'basic')
    assert homogeneous['carbs_g'] is not None
    assert NutritionAnalysisResponse.model_validate(
        homogeneous).carbohydrate_summary['basis'] == 'available'


@pytest.mark.parametrize('corruption', [
    'numeric_combined_carbs', 'missing_fat', 'wrong_energy', 'missing_detail',
    'missing_definition', 'unknown_definition', 'missing_detail_macro',
    'nan_detail_macro', 'duplicate_index',
])
def test_mixed_exception_cannot_mask_missing_or_incoherent_nutrition(corruption):
    result = mixed_result()
    if corruption == 'numeric_combined_carbs':
        result['carbs_g'] = 45
    elif corruption == 'missing_fat':
        result['fat_g'] = None
    elif corruption == 'wrong_energy':
        result['calories'] += 5
    elif corruption == 'missing_detail':
        result['details'].pop()
    elif corruption == 'missing_definition':
        result['details'][1].pop('carbohydrate_basis')
    elif corruption == 'unknown_definition':
        result['details'][1]['carbohydrate_basis'] = 'unknown'
    elif corruption == 'missing_detail_macro':
        result['details'][0]['nutrients'].pop('fat_g')
    elif corruption == 'nan_detail_macro':
        result['details'][0]['nutrients']['fat_g'] = float('nan')
    elif corruption == 'duplicate_index':
        result['details'][1]['item_index'] = 0
    with pytest.raises(ValueError):
        NutritionAnalysisResponse.model_validate(result)


def test_returned_reference_evidence_is_independent_of_later_catalogue_changes(monkeypatch):
    snapshot = deepcopy(catalogue())
    monkeypatch.setattr(meal_engine, 'catalogue', lambda: snapshot)
    result = evaluate_mode(draft_for(FOODS['dish_266']), 'basic')
    saved = deepcopy(result)
    food = next(food for food in snapshot['foods'] if food['id'] == 'dish_266')
    food['measured_reference']['nutrients']['calories'] = 999
    food['measured_reference']['source']['name'] = 'Changed later'
    food['method'] = 'Changed later'
    assert result == saved
