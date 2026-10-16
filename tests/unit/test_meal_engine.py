from copy import deepcopy

import pytest

from services.common.meal_engine import ExtractedItem, apply_answers, catalogue, evaluate
from services.common.schemas import NutritionAnalysisResponse


def item(**kwargs):
    return ExtractedItem(name='餐食', **kwargs).model_dump()


def test_catalogue_provenance_and_referential_integrity():
    foods = {f['id']:f for f in catalogue()['foods']}
    assert sum(f['kind']=='ingredient' for f in foods.values()) >= 100
    assert sum(f['kind']=='recipe' for f in foods.values()) >= 50
    for food in foods.values():
        if food['kind']=='ingredient':
            assert food['source']['license']=='CC0-1.0'
            assert food['source']['id'] == str(food['fdc_id'])
            assert len(food['nutrients'])==4
            assert all(value >= 0 for value in food['nutrients'].values())
        else:
            assert set(food['recipe']['ingredients']) <= foods.keys()
            assert food['recipe']['yield_g'] > 0


def test_missing_method_then_oil_never_produces_partial_totals():
    draft = [item(food_id='chicken', grams=200, weight_basis='raw')]
    result = evaluate(draft)
    assert result['calories'] is None
    assert result['questions'][0]['key']=='0.preparation'
    draft = apply_answers(draft, {'0.preparation':'stir_fried'})
    assert evaluate(draft)['questions'][0]['key']=='0.oil_g'
    draft = apply_answers(draft, {'0.oil_g':5})
    result = evaluate(draft)
    assert not result['questions']
    assert result['calories']==284.2  # USDA 120kcal/100g chicken + 884kcal/100g soybean oil
    assert result['fat_g'] > 5


def test_unknown_food_does_not_discard_it_or_return_partial_meal():
    draft = [item(food_id='rice', grams=100, weight_basis='cooked', preparation='boiled'),
             item(food_id=None, grams=100)]
    assert evaluate(draft)['calories'] is None
    assert evaluate(draft)['details']==[]
    draft = apply_answers(draft, {'1.food_id':'chocolate_milk'})
    assert draft[1]['weight_basis'] is None


def test_raw_cooked_weight_is_not_implicitly_converted():
    draft = [item(food_id='rice_raw',grams=150,weight_basis='cooked',preparation='boiled')]
    result = evaluate(draft)
    assert result['calories'] is None
    assert result['questions'][0]['key']=='0.weight_basis'


def test_recipe_confirmation_custom_yield_and_oil_change():
    draft = [item(food_id='dish_001',grams=200,weight_basis='cooked')]
    first = evaluate(draft)
    assert first['calories'] is None
    recipe = deepcopy(first['questions'][0]['recipe'])
    draft = apply_answers(draft, {'0.recipe':recipe})
    result = evaluate(draft)
    assert not result['questions']
    other = deepcopy(draft)
    other[0]['recipe']['ingredients']['oil'] += 10
    assert evaluate(other)['calories']-result['calories'] == pytest.approx(44.2,abs=.1)
    other[0]['recipe']['yield_g'] *= 2
    assert evaluate(other)['calories'] < result['calories']
    assert '整锅' in result['details'][0]['assumptions'][1]


def test_explicit_recipe_facts_prefill_but_never_auto_approve():
    draft = [item(food_id='dish_001', grams=200, weight_basis='cooked',
                  recipe_ingredients={'oil':7,'egg_raw':200},recipe_yield_g=450)]
    result=evaluate(draft)
    assert result['calories'] is None
    assert result['questions'][0]['recipe']['ingredients']['oil']==7
    assert result['questions'][0]['recipe']['yield_g']==450


@pytest.mark.parametrize('answers', [
    {'0.calories':100}, {'0.grams':-1}, {'0.grams':True},
    {'0.grams':float('nan')}, {'0.grams':float('inf')}, {'0.grams':10001},
])
def test_unissued_or_invalid_answers_rejected(answers):
    with pytest.raises(ValueError):
        apply_answers([item(food_id='rice')], answers)


def test_forged_recipe_nutrients_and_zero_yield_rejected():
    draft=[item(food_id='dish_001', grams=200, weight_basis='cooked')]
    recipe=deepcopy(evaluate(draft)['questions'][0]['recipe'])
    recipe['yield_g']=0
    with pytest.raises(ValueError):
        apply_answers(draft, {'0.recipe':recipe})
    recipe['yield_g']=500
    recipe['ingredients']['calories']=1
    with pytest.raises(ValueError):
        apply_answers(draft, {'0.recipe':recipe})


def test_response_cannot_mix_questions_and_totals():
    with pytest.raises(ValueError):
        NutritionAnalysisResponse(calories=100, protein_g=1, carbs_g=2, fat_g=3,
                                  questions=[{'key':'a'}],draft=[{'a':1}])


def test_cooked_food_preparation_mismatch_requires_rematching():
    result=evaluate([item(food_id='egg',grams=100,weight_basis='cooked',
                          preparation='fried',oil_g=5)])
    assert result['calories'] is None
    assert result['questions'][0]['key']=='0.food_id'


def test_basic_uses_visible_defaults_without_mutating_user_facts():
    from services.common.meal_engine import evaluate_mode
    draft=[item(food_id='dish_001')]
    result=evaluate_mode(draft,'basic')
    assert result['calories'] > 0
    assert result['questions']==[]
    assert result['draft'][0]['grams'] is None
    assert not result['draft'][0].get('recipe_confirmed')
    notes=' '.join(result['details'][0]['assumptions'])
    assert '未逐项核实' in notes and '每份 200g' in notes
    advanced=evaluate_mode(result['draft'],'advanced')
    assert advanced['calories'] is None
    assert {'0.grams','0.recipe','0.weight_basis'} <= {q['key'] for q in advanced['questions']}


def test_basic_explicit_grams_preserved_unknown_foods_not_invented():
    from services.common.meal_engine import evaluate_mode
    draft=[item(food_id='chocolate_milk',grams=200)]
    result=evaluate_mode(draft,'basic')
    food=next(f for f in catalogue()['foods'] if f['id']=='chocolate_milk')
    assert result['calories']==round(food['nutrients']['calories']*2,1)
    assert result['details'][0]['grams']==200
    unknown=evaluate_mode([item(food_id=None)],'basic')
    assert unknown['calories'] is None
    assert unknown['questions'][0]['kind']=='food'


def test_basic_respects_explicit_piece_count_and_labels_weight_assumption():
    from services.common.meal_engine import evaluate_mode
    result=evaluate_mode([item(food_id='egg',portion_count=2,portion_unit='piece')],'basic')
    assert result['details'][0]['grams']==100
    assert result['draft'][0]['grams'] is None
