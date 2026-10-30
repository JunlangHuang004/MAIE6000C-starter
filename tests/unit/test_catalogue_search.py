"""Prompt retrieval is bounded context, not permission to substitute food identities."""
from services.common.catalogue_search import catalogue_candidates
from services.common.food_matching import ground_food_items
from services.common.meal_engine import ExtractedItem, catalogue


def ids(text, history=None):
    return {food['id'] for food in catalogue_candidates(text, history)}


def test_known_chinese_meal_retrieves_names_and_recipe_ingredients():
    found = ids('200克宫保鸡丁，不加花生，整锅油5克；100克熟白米饭')
    assert {'dish_003', 'rice', 'peanut', 'oil'} <= found
    assert len(found) < 30
    assert 'dish_010' not in found


def test_existing_english_aliases_remain_retrievable():
    assert 'rice' in ids('200 g cooked white rice, no added oil')
    assert 'dish_144' in ids('Garlic stir-fried Chinese broccoli (gai lan), 200 g')


def test_assistant_and_server_copied_draft_do_not_supply_search_evidence():
    found = ids('100克米饭', [
        {'role':'assistant','content':'要不要选择清蒸鲤鱼'},
        {'role':'user','content':'已回答：{}\n当前餐食资料：清蒸鲤鱼'},
    ])
    assert 'rice' in found and 'dish_010' not in found
    assert 'dish_010' in ids('100克米饭', [{'role':'user','content':'另有200克清蒸鲤鱼'}])


def test_related_candidate_is_never_matching_authority():
    text = '100克火星米饭'
    assert 'rice' in ids(text)
    result = ground_food_items([ExtractedItem(
        name='火星米饭', source_text='火星米饭', food_id='rice', grams=100)], text)
    assert result[0].food_id is None
    assert ids('200克月球紫晶兽肉') == set()


def test_context_size_remains_bounded_as_catalogue_grows():
    text = '、'.join(food['name'] for food in catalogue()['foods'])
    candidates = catalogue_candidates(text)
    assert len(candidates) <= 120
    assert len({food['id'] for food in candidates}) == len(candidates)
    assert all(food in catalogue()['foods'] for food in candidates)
