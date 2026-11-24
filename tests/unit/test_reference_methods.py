"""Cooking-method evidence must not turn negated or mixed steps into matches."""
import pytest

from services.common import recipe_references as references
from services.common.preparations import recognized_preparations


@pytest.mark.parametrize('food_id,ingredients', [
    ('dish_024', ['eggplant']),
    ('dish_028', ['shiitake', 'tofu']),
])
def test_bare_braising_verb_retains_identical_main_ingredient_references(food_id, ingredients):
    foods = references.reference_shortlist(ingredients, 'braised')
    assert food_id in {food['id'] for food in foods}
    assert all(set(food['recipe']['ingredients']) - references.SEASONINGS == set(ingredients)
               for food in foods)


def test_non_fried_eggplant_is_braised_and_never_fried():
    recipe = next(food for food in references.catalogue()['foods'] if food['id'] == 'dish_024')
    assert recipe['method'] == '烧（非油炸版）'
    assert references._method_matches(recipe, 'braised')
    assert not references._method_matches(recipe, 'fried')
    assert 'dish_024' not in {
        food['id'] for food in references.reference_shortlist(['eggplant', 'pork'], 'braised')}


@pytest.mark.parametrize('method,expected', [
    ('烧（非油炸版）', {'braised'}),
    ('不煎炸，改为蒸熟', {'steamed'}),
    ('不用油炸或煎制，直接红烧', {'braised'}),
    ('焯熟后拌匀，不用炸', {'boiled', 'as_served'}),
    ('炒（非过油版）', {'stir_fried'}),
    ('非水煮版，改用清蒸', {'steamed'}),
    ('先炸后红烧，不再油炸', {'fried', 'braised'}),
    ('非牛肉末配方，鸡肉炒熟', {'stir_fried'}),
    ('汤、煲、蒜香、香辣', set()),
    ('叉烧肉、照烧鸡腿', set()),
    ('烧烤', {'roasted'}),
    ('紅燒豆腐', {'braised'}),
    ('燒烤', {'roasted'}),
    ('燒（非油炸版）', {'braised'}),
    ('炖與燉，焖與燜，卤與滷', {'braised'}),
    ('燒開後涼拌', {'boiled', 'as_served'}),
    ('叉燒肉、照燒雞腿、燒賣、燒麥', set()),
    ('清炒（無需油炸）', {'stir_fried'}),
    ('無須預先煎炸，直接燉煮', {'braised', 'boiled'}),
    ('不採用過油，直接紅燒', {'braised'}),
    ('未經油炸，直接燜熟', {'braised'}),
    ('不燉或燜，改用蒸', {'steamed'}),
    ('沒有滷製，改為清蒸', {'steamed'}),
    ('不煎製與炸製，直接清蒸', {'steamed'}),
    ('Stir-fried chicken', {'stir_fried'}),
    ('stir fried chicken', {'stir_fried'}),
    ('pan-fried or deep fried fish', {'fried'}),
    ('not fried or grilled; steamed instead', {'steamed'}),
    ('non-fried braised eggplant', {'braised'}),
    ('cold tossed chicken salad', {'as_served'}),
    ('boiled or blanched or poached chicken', {'boiled'}),
    ('roasted, baked or grilled', {'roasted'}),
    ('braised and stewed', {'braised'}),
    ('not raw; steamed', {'steamed'}),
    ('strawberry and friedrich', set()),
])
def test_normalized_methods_ignore_negation_without_erasing_positive_steps(method, expected):
    assert recognized_preparations(method) == expected


@pytest.mark.parametrize('method,preparation', [
    ('烧', 'braised'), ('红烧', 'braised'), ('焖熟', 'braised'), ('炖煮', 'braised'),
    ('卤制', 'braised'), ('白灼', 'boiled'), ('熬粥', 'boiled'), ('烧开', 'boiled'),
    ('生食', 'raw'), ('清蒸', 'steamed'), ('盐焗', 'roasted'), ('煎炸', 'fried'),
    ('清炒（无需油炸）', 'stir_fried'), ('先煮熟后炒', 'stir_fried'),
    ('焯熟后拌醋', 'as_served'), ('蒸熟后凉拌', 'as_served'),
    ('烧（不煎或炸）', 'braised'),
    ('紅燒豆腐（無需油炸）', 'braised'), ('燒烤', 'roasted'),
])
def test_supported_method_vocabulary_and_compatible_preparatory_steps(method, preparation):
    assert references._method_matches({'method': method}, preparation)


@pytest.mark.parametrize('method,preparation', [
    ('先炸后煮', 'boiled'), ('先煎后红烧', 'braised'), ('炸后焖熟', 'braised'),
    ('烤后炖煮', 'braised'), ('先煎后炒', 'stir_fried'), ('先炸后蒸', 'steamed'),
    ('拌匀后蒸熟', 'as_served'), ('糖拌匀后煎熟', 'as_served'),
    ('炒熟后煮汤', 'stir_fried'), ('先煮熟后炒', 'boiled'),
    ('炖煮', 'boiled'), ('非生食，煮熟', 'raw'), ('凉拌', 'other'),
    ('先煎後紅燒', 'braised'), ('燒烤', 'braised'), ('非紅燒版，清蒸', 'braised'),
])
def test_incompatible_mixed_or_negated_methods_are_not_offered(method, preparation):
    assert not references._method_matches({'method': method}, preparation)


def test_explicit_preparation_metadata_controls_compatibility():
    food = {'method': '先炸后红烧', 'preparations': ['boiled', 'as_served']}
    assert references._method_matches(food, 'boiled')
    assert references._method_matches(food, 'as_served')
    assert not references._method_matches(food, 'fried')
    assert not references._method_matches(food, 'braised')
    assert not references._method_matches({'method': '红烧', 'preparations': []}, 'braised')


@pytest.mark.parametrize('food_id,preparation', [
    ('dish_003', 'stir_fried'), ('dish_007', 'stir_fried'), ('dish_036', 'stir_fried'),
    ('dish_255', 'as_served'), ('dish_153', 'as_served'), ('dish_351', 'fried'),
    ('dish_109', 'boiled'), ('dish_109', 'as_served'), ('dish_355', 'steamed'),
])
def test_existing_catalogue_compatibility_is_preserved(food_id, preparation):
    food = next(food for food in references.catalogue()['foods'] if food['id'] == food_id)
    assert references._method_matches(food, preparation)
