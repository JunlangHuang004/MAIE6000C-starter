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
    if without_mass != value and re.fullmatch(
            r'(?:实际|實際|吃了|吃下|可食部分|还是|還是|仍是|是|为|為|共|总共|'
            r'熟重|生重|\s)+', without_mass):
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


def _single_wrapped_name(mention, texts):
    """Accept one exact reviewed name surrounded only by bounded meal details."""
    normalized, offsets = [], []
    for index, character in enumerate(mention):
        part = normalize_name(character)
        normalized.extend(part)
        offsets.extend([index] * len(part))
    normalized = ''.join(normalized)
    if normalized != normalize_name(mention):
        # Do not invent source offsets for combining-character normalization.
        return None
    matches = set()
    for alias, food_ids in name_index().items():
        if len(food_ids) != 1:
            continue
        position = normalized.find(alias)
        while position >= 0:
            start = offsets[position]
            end = offsets[position + len(alias) - 1] + 1
            # Keep closing parentheses that belong to a reviewed food name.
            for opening, closing in (('(', ')'), ('（', '）')):
                span = mention[start:end]
                if span.count(opening) > span.count(closing):
                    closing_at = end
                    while closing_at < len(mention) and mention[closing_at].isspace():
                        closing_at += 1
                    if mention[closing_at:closing_at + 1] == closing:
                        end = closing_at + 1
            span = mention[start:end]
            if (normalize_name(span) == alias and is_user_mention(span, [mention])
                    and is_user_mention(span, texts)):
                matches.add((start, end, next(iter(food_ids))))
            position = normalized.find(alias, position + 1)
    # Nested aliases for the same occurrence are one name, not a second food.
    maximal = [match for match in matches if not any(
        other[0] <= match[0] and match[1] <= other[1] and other[:2] != match[:2]
        for other in matches)]
    if len(maximal) != 1:
        return None
    start, end, food_id = maximal[0]
    remaining = unicodedata.normalize('NFKC', mention[:start] + mention[end:])
    if not all(_detail_clause(clause) for clause in _SPLIT.split(remaining)):
        return None
    return mention[start:end], food_id


def _current_identity_texts(texts):
    """Keep the last explicit replacement and every subsequent user utterance."""
    for index in range(len(texts) - 1, -1, -1):
        text = texts[index]
        consumed_ingredients = re.fullmatch(
            r'\s*(?:(?:改成|改为|改為|换成|換成|更正为|更正為)\s*)?'
            r'(?:这次实际吃下的食材|這次實際吃下的食材|实际吃下的食材|實際吃下的食材)'
            r'\s*(?:是|为|為)?\s*[:：]\s*(.+)', text, re.S,
        )
        if consumed_ingredients:
            # Capture the whole multiline list, including any unsupported additions.
            # A whole-pot ingredient list alone must not silently become intake.
            return [consumed_ingredients.group(1), *texts[index + 1:]]
        replacement = re.fullmatch(
            r'\s*(?:改成|改为|改為|换成|換成|更正为|更正為|其实是|其實是|'
            r'\bchange\b[^\n]+?\bto\b|\breplace\b[^\n]+?\bwith\b)\s*(.+)',
            text, re.I | re.S,
        )
        if replacement:
            remaining = re.sub(_MASS, '', replacement.group(1), flags=re.I)
            remaining = re.sub(
                r'[\s,，。.;；]|熟重|生重|少油|多油|不加油|去骨|去壳', '', remaining)
            if remaining:
                # Quantity-only replies do not reset an earlier identity replacement.
                return [replacement.group(1), *texts[index + 1:]]
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
        if grounded and not candidates:
            wrapped = _single_wrapped_name(mention, texts)
            if wrapped is not None:
                mention, food_id = wrapped
                candidates = {food_id}
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
