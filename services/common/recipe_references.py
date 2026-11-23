"""Explicit approximate references, separate from exact food identity matching."""
import re
from copy import deepcopy

from services.common.meal_engine import catalogue
from services.common.schemas import RecipeInferenceResponse, RecipeRecommendationResponse


MAX_REFERENCE_CANDIDATES = 30
# These must never supply the sole similarity between unrelated main foods.
SEASONINGS = frozenset({
    'water', 'salt', 'oil', 'sesame_oil', 'peanut_oil', 'canola_oil', 'olive_oil',
    'butter', 'sugar', 'honey', 'soy_sauce', 'vinegar', 'oyster_sauce', 'hoisin',
    'ketchup', 'starch', 'garlic', 'ginger', 'spring_onion', 'cilantro', 'chili',
    'black_pepper', 'white_pepper', 'chili_powder', 'curry_powder', 'cumin',
    'fish_sauce', 'yeast',
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
    """Require all and only the declared main ingredients, plus compatible preparation."""
    validate_reference_ingredients(ingredient_ids)
    primary = set(ingredient_ids) - SEASONINGS
    if not primary:
        return []
    matches = []
    for food in catalogue()['foods']:
        if food['kind'] != 'recipe' or not _method_matches(food, preparation):
            continue
        recipe_ids = {key for key, grams in food['recipe']['ingredients'].items() if grams > 0}
        if recipe_ids - SEASONINGS != primary:
            continue
        matches.append(food)
    return sorted(matches, key=lambda food: food['id'])[:MAX_REFERENCE_CANDIDATES]


def reference_candidate(food, ingredient_ids, provider):
    """Build display explanations from catalogue facts, never provider-written claims."""
    foods = validate_reference_ingredients(ingredient_ids)
    actual = {key for key, grams in food['recipe']['ingredients'].items() if grams > 0}
    declared = set(ingredient_ids)
    if not declared - SEASONINGS or actual - SEASONINGS != declared - SEASONINGS:
        raise ValueError('Reference explanations require identical main ingredients')
    differences_zh, differences_en = [], []
    for ids, zh, en in (
            (actual - declared, '参考配方另含调味料：', 'Additional reference seasonings: '),
            (declared - actual, '参考配方未含你选择的调味料：',
             'Declared seasonings absent from this reference: ')):
        if ids:
            differences_zh.append(zh + '、'.join(foods[key]['name'] for key in sorted(ids)))
            differences_en.append(en + ', '.join(key.replace('_', ' ') for key in sorted(ids)))
    differences_zh.append('调味料、全部用量和成品重量仍须逐项核对。')
    differences_en.append('Review seasonings, all quantities and the finished batch weight.')
    reason_zh = '主要食材一致，做法匹配；调味料和全部用量仍须核对。'
    reason_en = 'The main ingredients match and preparation is compatible; '
    reason_en += 'review seasonings and all quantities.'
    if provider == 'demo':
        reason_zh += '这是离线规则结果，不是模型推荐。'
        reason_en += ' This is an offline rule-based result, not a model recommendation.'
    return {'food_id': food['id'], 'reason_zh': reason_zh, 'reason_en': reason_en,
            'differences_zh': differences_zh, 'differences_en': differences_en}


def validated_reference_candidates(value, ingredient_ids, preparation):
    response = RecipeRecommendationResponse.model_validate(value)
    allowed = {food['id']: food for food in reference_shortlist(ingredient_ids, preparation)}
    ids = [candidate.food_id for candidate in response.candidates]
    if len(ids) != len(set(ids)) or set(ids) - allowed.keys():
        raise ValueError('The recommendation included an invalid or incompatible recipe')
    candidates = [{**reference_candidate(allowed[candidate.food_id], ingredient_ids,
                                        response.provider),
                   'name': allowed[candidate.food_id]['name'],
                   'method': allowed[candidate.food_id]['method']}
                  for candidate in response.candidates]
    return {'provider': response.provider, 'candidates': candidates}


def validated_reference_inference(value):
    """Treat inferred ingredients as reviewable suggestions, never observed facts."""
    response = RecipeInferenceResponse.model_validate(value)
    validate_reference_ingredients(response.ingredient_ids)
    if response.status == 'suggested' and not set(response.ingredient_ids) - SEASONINGS:
        raise ValueError('An inferred suggestion needs at least one main ingredient')
    return response.model_dump()


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
