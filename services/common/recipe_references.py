"""Explicit approximate references, separate from exact food identity matching."""
import re
from copy import deepcopy

from services.common.meal_engine import catalogue
from services.common.schemas import RecipeRecommendationResponse


MAX_REFERENCE_CANDIDATES = 30
# These must never supply the sole similarity between unrelated main foods.
SEASONINGS = frozenset({
    'water', 'salt', 'oil', 'sesame_oil', 'peanut_oil', 'canola_oil', 'olive_oil',
    'butter', 'sugar', 'honey', 'soy_sauce', 'vinegar', 'oyster_sauce', 'hoisin',
    'ketchup', 'starch', 'garlic', 'ginger', 'spring_onion', 'cilantro', 'chili',
    'black_pepper', 'white_pepper', 'chili_powder', 'curry_powder', 'cumin',
    'fish_sauce', 'yeast',
})
ANIMAL_INGREDIENTS = frozenset({
    'chicken', 'chicken_roast', 'chicken_stew', 'chicken_thigh', 'chicken_wing',
    'chicken_skin', 'chicken_skin_stewed', 'chicken_meat_stewed', 'chicken_gizzard',
    'chicken_heart', 'chicken_liver', 'pork_belly', 'pork', 'pork_ground', 'pork_ribs',
    'pork_heart', 'pork_kidney', 'pork_intestine', 'pork_stomach', 'pork_ear',
    'pork_feet', 'pork_feet_cooked', 'liver', 'pork_liver_cooked', 'beef',
    'beef_chunk', 'beef_lean', 'lamb', 'lamb_leg', 'duck', 'duck_skin', 'duck_roast',
    'goose', 'rabbit', 'salmon', 'salmon_cooked', 'cod', 'tilapia', 'carp',
    'shrimp', 'shrimp_cooked', 'squid', 'clam', 'mussel', 'crab', 'scallop',
    'octopus', 'octopus_cooked', 'ham',
})


def validate_reference_ingredients(ingredient_ids):
    foods = {food['id']: food for food in catalogue()['foods']}
    if len(set(ingredient_ids)) != len(ingredient_ids) or any(
            foods.get(food_id, {}).get('kind') != 'ingredient' for food_id in ingredient_ids):
        raise ValueError('请选择不重复的目录食材；不能填写菜谱或未知食物编号。')
    return foods


def _method_matches(food, preparation):
    if food.get('preparations'):
        return preparation in food['preparations']
    text = food['method']
    patterns = {
        'raw': r'生食', 'as_served': r'凉拌|拌匀|拌醋|糖拌',
        'boiled': r'煮|焯|汆|氽', 'steamed': r'蒸', 'roasted': r'烤|焗',
        'stir_fried': r'炒', 'fried': r'煎|炸', 'braised': r'炖|焖|红烧|卤|烧制',
    }
    if preparation == 'other':
        # "Other" does not establish a compatible cooking method.
        return False
    if preparation in {'boiled', 'raw', 'as_served'} and re.search(r'煎|炸|烤|焗', text):
        return False
    if preparation == 'stir_fried' and re.search(r'蒸|煮汤|炖|焖|煎|炸|烤', text):
        return False
    return re.search(patterns[preparation], text) is not None


def reference_shortlist(ingredient_ids, preparation):
    """Bound model input using user-declared material ingredients and preparation."""
    validate_reference_ingredients(ingredient_ids)
    primary = set(ingredient_ids) - SEASONINGS
    if not primary:
        return []
    declared_animal = primary & ANIMAL_INGREDIENTS
    ranked = []
    for food in catalogue()['foods']:
        if food['kind'] != 'recipe' or not _method_matches(food, preparation):
            continue
        recipe_ids = set(food['recipe']['ingredients'])
        common = primary & recipe_ids
        if not common or (declared_animal and not declared_animal & recipe_ids):
            continue
        score = (-len(common), len(primary - recipe_ids), len(recipe_ids - SEASONINGS - primary))
        ranked.append((score, food['id'], food))
    ranked.sort(key=lambda row: (row[0], row[1]))
    return [food for _, _, food in ranked[:MAX_REFERENCE_CANDIDATES]]


def validated_reference_candidates(value, ingredient_ids, preparation):
    response = RecipeRecommendationResponse.model_validate(value)
    allowed = {food['id']: food for food in reference_shortlist(ingredient_ids, preparation)}
    ids = [candidate.food_id for candidate in response.candidates]
    if len(ids) != len(set(ids)) or set(ids) - allowed.keys():
        raise ValueError('The recommendation included an invalid or incompatible recipe')
    candidates = [{**candidate.model_dump(), 'name': allowed[candidate.food_id]['name'],
                   'method': allowed[candidate.food_id]['method']}
                  for candidate in response.candidates]
    return {'provider': response.provider, 'candidates': candidates}


def validate_reference_selection(selection):
    """Validate durable provenance again before producing any nutrition detail."""
    if not isinstance(selection, dict) or selection.get('acknowledged') is not True:
        raise ValueError('Missing explicit approximate-reference acknowledgment')
    food = next((food for food in catalogue()['foods']
                 if food['id'] == selection.get('source_food_id')
                 and food['kind'] == 'recipe'), None)
    if food is None or selection.get('source_name') != food['name']:
        raise ValueError('Invalid selected reference recipe')
    if (not isinstance(selection.get('original_name'), str)
            or not selection['original_name'].strip()):
        raise ValueError('Missing original unknown-food identity')
    return deepcopy(selection)
