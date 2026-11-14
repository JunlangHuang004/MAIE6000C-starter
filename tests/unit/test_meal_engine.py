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


@pytest.mark.parametrize('mode', ['basic', 'advanced'])
def test_unknown_food_does_not_discard_it_or_return_partial_meal(mode):
    from services.common.meal_engine import evaluate_mode
    draft = [item(food_id='rice', grams=100, weight_basis='cooked', preparation='boiled'),
             ExtractedItem(name='火星豉油鸡', source_text='火星豉油鸡', grams=200).model_dump()]
    result = evaluate_mode(draft, mode)
    assert all(result[key] is None for key in ('calories', 'protein_g', 'fat_g', 'carbs_g'))
    assert result['details'] == []
    assert result['interpreted_food_text'] is None
    assert result['draft'] == draft
    unsupported = next(q for q in result['questions'] if q['kind'] == 'unsupported')
    assert unsupported['key'] == '1.food_id'
    assert '火星豉油鸡' in unsupported['label'] and '数据库未找到' in unsupported['label']
    assert 'options' not in unsupported
    with pytest.raises(ValueError, match='没有对应的食物记录'):
        apply_answers(draft, {'1.food_id':'dish_010'}, mode)
    assert draft[1]['food_id'] is None


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
    assert unknown['questions'][0]['kind']=='unsupported'


@pytest.mark.parametrize('food_id,unit,count', [
    ('dish_005', 'piece', 3),
    ('dish_252', 'piece', 4),
    ('rice', 'bowl', 1),
    ('milk', 'cup', 1),
])
def test_basic_asks_for_grams_when_count_unit_has_no_explicit_conversion(food_id, unit, count):
    from services.common.meal_engine import evaluate_mode
    draft = [item(food_id=food_id, portion_count=count, portion_unit=unit)]
    original = deepcopy(draft)
    result = evaluate_mode(draft, 'basic')
    assert result['draft'] == original and draft == original
    assert [q['key'] for q in result['questions']] == ['0.grams']
    assert result['questions'][0]['kind'] == 'number'
    assert result['details'] == [] and result['interpreted_food_text'] is None
    assert all(result[key] is None for key in ('calories', 'protein_g', 'carbs_g', 'fat_g'))
    answered = apply_answers(draft, {'0.grams': 120}, 'basic')
    completed = evaluate_mode(answered, 'basic')
    assert completed['questions'] == []
    assert completed['details'][0]['grams'] == 120
    assert completed['details'][0]['quantity_provenance']['kind'] == 'user_grams'
    assert completed['draft'][0]['portion_count'] == count


def test_missing_piece_conversion_with_explicit_oil_waits_for_weight_before_scaling_recipe():
    from services.common.meal_engine import evaluate_mode
    draft = [item(food_id='dish_252', portion_count=4, portion_unit='piece', oil_g=5)]
    pending = evaluate_mode(draft, 'basic')
    assert [q['key'] for q in pending['questions']] == ['0.grams']
    assert pending['calories'] is None and pending['details'] == []
    assert pending['draft'][0]['oil_g'] == 5
    answered = apply_answers(draft, {'0.grams': 120}, 'basic')
    completed = evaluate_mode(answered, 'basic')
    explicit = evaluate_mode([item(food_id='dish_252', grams=120, oil_g=5)], 'basic')
    assert completed['calories'] == explicit['calories']
    assert completed['details'][0]['grams'] == 120


def test_basic_supported_piece_reference_remains_a_labelled_assumption():
    from services.common.meal_engine import evaluate_mode
    result = evaluate_mode([
        item(food_id='dish_241', portion_count=10, portion_unit='piece')], 'basic')
    assert result['questions'] == []
    assert result['details'][0]['grams'] == 200
    assert result['details'][0]['quantity_provenance']['reference_grams'] == 20
    assert result['draft'][0]['grams'] is None


def test_basic_boiled_egg_count_uses_explicit_large_egg_reference_without_mutating_facts():
    from services.common.meal_engine import evaluate_mode
    egg = next(food for food in catalogue()['foods'] if food['id'] == 'egg')
    assert egg['portion_weights_g']['piece'] == 50
    assert 'large hard-cooked egg, shell removed' in egg['portion_reference']['description']
    assert 'ars.usda.gov' in egg['portion_reference']['url']
    draft = [item(food_id='egg', portion_count=2, portion_unit='piece')]
    result = evaluate_mode(draft, 'basic')
    assert result['questions'] == [] and result['calories'] == 155
    assert result['details'][0]['grams'] == 100
    assert result['details'][0]['quantity_provenance']['reference_grams'] == 50
    assert '每个 50g' in ' '.join(result['details'][0]['assumptions'])
    assert result['draft'][0]['grams'] is None
    assert evaluate_mode(result['draft'], 'advanced')['calories'] is None


def test_one_unconverted_count_blocks_partial_total_for_the_entire_meal():
    from services.common.meal_engine import evaluate_mode
    result = evaluate_mode([
        item(food_id='rice', grams=100),
        item(food_id='dish_005', portion_count=3, portion_unit='piece'),
    ], 'basic')
    assert [q['key'] for q in result['questions']] == ['1.grams']
    assert result['calories'] is None and result['details'] == []


@pytest.mark.parametrize('food_id', ['dish_016', 'dish_349'])
def test_no_oil_recipe_clears_cooking_oils_preserves_other_ingredients_and_requires_review(food_id):
    from services.common.meal_engine import evaluate_mode
    food = next(food for food in catalogue()['foods'] if food['id'] == food_id)
    original = deepcopy(food['recipe'])
    draft = [item(food_id=food_id, grams=100, weight_basis='cooked', oil_g=0)]
    review = evaluate_mode(draft, 'advanced')
    assert review['calories'] is None
    recipe_question = next(q for q in review['questions'] if q['kind'] == 'recipe')
    reviewed = recipe_question['recipe']
    for ingredient, grams in original['ingredients'].items():
        assert reviewed['ingredients'][ingredient] == (
            0 if ingredient in {'oil', 'sesame_oil'} else grams)
    assert reviewed['yield_g'] == original['yield_g']
    accepted = apply_answers(draft, {'0.recipe': reviewed}, 'advanced')
    advanced = evaluate_mode(accepted, 'advanced')
    basic = evaluate_mode(draft, 'basic')
    assert basic['calories'] == advanced['calories']
    if food_id == 'dish_016':
        assert basic['calories'] == 25.9
    assert catalogue()['foods'][catalogue()['foods'].index(food)]['recipe'] == original
    assert draft[0]['recipe_ingredients'] is None


def test_positive_recipe_oil_does_not_reinterpret_other_oil_mixtures():
    draft = [item(food_id='dish_349', grams=100, weight_basis='cooked', oil_g=5)]
    question = next(q for q in evaluate(draft)['questions'] if q['kind'] == 'recipe')
    assert question['recipe']['ingredients']['sesame_oil'] == 10
    assert question['recipe']['ingredients']['oil'] == 5 * question['recipe']['yield_g'] / 100
