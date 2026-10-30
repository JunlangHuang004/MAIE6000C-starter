"""Bound model context to relevant catalogue records; never authorize a food match."""
from functools import lru_cache

from services.common.food_matching import (
    is_user_mention, matching_aliases, normalize_name, user_texts,
)
from services.common.meal_engine import catalogue


@lru_cache(maxsize=1)
def _search_rows():
    return [
        (food, [(name, normalize_name(name)) for name in dict.fromkeys(
            [food['name'], *food['aliases'], *matching_aliases().get(food['id'], [])])])
        for food in catalogue()['foods']
    ]


def catalogue_candidates(food_text, history=None, *, primary_limit=60, total_limit=120):
    """Retrieve exact name/alias spans and bounded recipe ingredient context.

    Substring hits may provide parsing context, but only the separate grounding
    guard can accept an identity. An absent name must remain absent even if a
    related ingredient appears in this shortlist. No fuzzy food substitution.
    """
    texts = user_texts(food_text, history)
    normalized = [normalize_name(text) for text in texts]
    hits = []
    for food, aliases in _search_rows():
        matched = [(name, key) for name, key in aliases
                   if key and any(key in text for text in normalized)]
        if not matched:
            continue
        # Whole food mentions outrank ingredient names embedded in another dish.
        score = max((is_user_mention(name, texts), len(key)) for name, key in matched)
        hits.append((score, food))
    hits.sort(key=lambda pair: (-pair[0][0], -pair[0][1], pair[1]['id']))
    selected = [food for _, food in hits[:primary_limit]]
    selected_ids = {food['id'] for food in selected}
    foods = {food['id']: food for food in catalogue()['foods']}
    for food in list(selected):
        for fid in food.get('recipe', {}).get('ingredients', {}):
            if fid not in selected_ids and len(selected) < total_limit:
                selected.append(foods[fid])
                selected_ids.add(fid)
    return selected
