"""Fail-closed identity checks: a valid catalogue ID alone is not a food match."""
import json
import re
import unicodedata
from functools import lru_cache

from services.common.meal_engine import DATA, ExtractedItem, catalogue


def normalize_name(value):
    """Ignore typography, never remove meaningful ingredients or preparation words."""
    return re.sub(r'[\W_]+', '', unicodedata.normalize('NFKC', value).casefold())


@lru_cache(maxsize=1)
def matching_aliases():
    return json.loads((DATA / 'matching_aliases.json').read_text())['aliases']


@lru_cache(maxsize=1)
def name_index():
    index = {}
    for food in catalogue()['foods']:
        names = [food['name'], *food['aliases'], *matching_aliases().get(food['id'], [])]
        for name in names:
            index.setdefault(normalize_name(name), set()).add(food['id'])
    return index


def user_texts(food_text, history):
    texts = [food_text]
    for entry in history or []:
        if entry.get('role') != 'user':
            continue
        text = entry.get('content', '')
        # This is a server-generated copy of the old draft, not new naming evidence.
        if text.startswith('已回答：') and '\n当前餐食资料：' in text:
            continue
        if text not in texts:
            texts.append(text)
    return texts


_NUMBER = r'(?:\d+(?:\.\d+)?|[零〇一二两兩三四五六七八九十百千半]+)'
_MASS = _NUMBER + r'\s*(?:千克|公斤|kg|grams?|克|g|斤|碗|个|個|份|杯)'
_SPLIT = re.compile(
    r'[,，;；。\n、]|(?<!\d)\.(?=\s|$)|\b(?:and|plus)\b|以及|还有|還有|另外|和', re.I)
_PREFIX = re.compile(
    r'(?:\s|[:：]|' + _MASS + r'|'
    r'我|今天|早餐|午餐|晚餐|午饭|晚饭|吃了|吃的|吃|有|一份|一碗|两个|兩個|'
    r'请估算|估算|请计算|计算|去壳|去殼|去骨|净重|淨重|的|'
    r'(?<![a-z])(?:i ate|i had|i have|for lunch|for dinner|for breakfast|'
    r'a serving of|one serving of|a portion of|one bowl of|a bowl of|'
    r'of the chinese dish|of|the|some)(?![a-z]))+',
    re.I,
)
_SUFFIX = re.compile(
    r'(?:\s|[.。:：()]|' + _MASS + r'|'
    r'熟重|生重|可食部分|净重|淨重|去壳|去殼|去骨|共|总共|總共|的|少油|多油|不加油|'
    r'(?<![a-z])(?:cooked edible weight|raw edible weight|edible weight|'
    r'cooked weight|raw weight|bones removed|without shell)(?![a-z]))+', re.I,
)


def _wrapper(value, pattern):
    return not value.strip() or pattern.fullmatch(value) is not None


def _ingredient_name(value):
    if normalize_name(value) in {'油', '用油', '花生', 'oil', 'addedoil', 'peanuts'}:
        return True
    ids = name_index().get(normalize_name(value), set())
    return len(ids) == 1 and all(
        f['kind'] == 'ingredient' for f in catalogue()['foods'] if f['id'] in ids)


def _detail_clause(value):
    """Only whole known detail forms may disappear from food coverage checks."""
    value = value.strip(' .。:：').casefold()
    if _wrapper(value, _PREFIX) or _wrapper(value, _SUFFIX):
        return True
    without_mass = re.sub(_MASS, '', value, flags=re.I)
    if without_mass != value and (
            _wrapper(without_mass, _PREFIX) or _wrapper(without_mass, _SUFFIX)):
        return True
    if re.fullmatch(r'(?:改成|改为|改為|换成|換成)?\s*' + _MASS + r'(?:熟重|生重|少油)?',
                    value, re.I):
        return True
    if re.fullmatch(r'(?:整锅|整鍋)?(?:成品|熟制成品|总重|總重)(?:为|是)?\s*' + _MASS,
                    value, re.I):
        return True
    ingredient = re.fullmatch(r'(?:整锅|整鍋)(.+?)\s*' + _MASS, value, re.I)
    if ingredient and _ingredient_name(ingredient[1]):
        return True
    excluded = re.fullmatch(r'(?:不加|no |with no )(.+)', value, re.I)
    if excluded and _ingredient_name(excluded[1]):
        return True
    return re.fullmatch(
        r'(?:edible weight measured before cooking|edible raw weight before cooking|'
        r'shells? removed|there is no additional oil|cooked|'
        r'i do not know its weight in grams|'
        r'drained cooked edible weight|the weight is cooked edible meat only|'
        r'all weights are (?:cooked )?edible weights?|'
        r'with \d+(?:\.\d+)?\s*g additional oil in this portion|'
        r'whole.batch oil\s*\d+(?:\.\d+)?\s*g|'
        r'finished batch(?: weight)?\s*\d+(?:\.\d+)?\s*g)', value, re.I,
    ) is not None


def is_user_mention(mention, texts):
    """Require the complete named food, not a substring of another dish.

    Bounded surrounding quantity/meal grammar is allowed. Unrecognized wording
    asks the user to restate the name instead of falling back to fuzzy matching.
    """
    needle = unicodedata.normalize('NFKC', mention).casefold().strip()
    if not needle:
        return False
    for text in texts:
        text = unicodedata.normalize('NFKC', text).casefold()
        for match in re.finditer(re.escape(needle), text):
            left = _SPLIT.split(text[:match.start()])[-1]
            right = _SPLIT.split(text[match.end():])[0]
            if _wrapper(left, _PREFIX) and _detail_clause(right):
                return True
    return False


def _current_identity_texts(texts):
    """Do not resurrect an earlier dish after an explicit name replacement."""
    latest = texts[-1]
    replacement = re.search(
        r'(?:改成|改为|改為|换成|換成|更正为|更正為|其实是|其實是|'
        r'\bchange\b.+?\bto\b|\breplace\b.+?\bwith\b)\s*(.+)', latest, re.I,
    )
    if replacement:
        remaining = re.sub(_MASS, '', replacement.group(1), flags=re.I)
        remaining = re.sub(r'[\s,，。.;；]|熟重|生重|少油|多油|不加油|去骨|去壳', '', remaining)
        if remaining:
            # Retain the replacement phrase itself so its grammar is not a food name.
            return [replacement.group(1)]
    return texts


def ground_food_items(items, food_text, history=None):
    """Clear unverified IDs before any mode-specific nutrient assumptions.

    Qwen must copy the original whole food mention in source_text. For older
    responses, the unchanged name can provide the same evidence. A unique exact
    reviewed name match determines identity, independently of Qwen's guessed ID.
    """
    texts = _current_identity_texts(user_texts(food_text, history))
    for item in items:
        mention = item.source_text or item.name
        grounded = is_user_mention(mention, texts)
        candidates = name_index().get(normalize_name(mention), set()) if grounded else set()
        if len(candidates) == 1:
            item.food_id = next(iter(candidates))
            item.name = mention
            item.source_text = mention
            continue
        item.food_id = None
        # Never show a hallucinated canonical dish as the unsupported user food.
        item.name = (mention if grounded else texts[-1])[:120]
        item.source_text = mention if grounded else None
        item.uncertainty = None
        item.recipe_ingredients = None
        item.recipe_yield_g = None
    if all(item.food_id is not None for item in items):
        # Do not let a model silently discard the unsupported half of a mixed
        # meal. Consume verified complete names, then inspect remaining clauses.
        verified = list(items)
        for text in texts:
            remaining = unicodedata.normalize('NFKC', text).casefold()
            for item in verified:
                remaining = remaining.replace(
                    unicodedata.normalize('NFKC', item.source_text).casefold(), '')
            for clause in _SPLIT.split(remaining):
                clause = clause.strip(' .。:：')
                if not _detail_clause(clause):
                    items.append(ExtractedItem(name=clause[:120], source_text=clause[:120]))
    return items
