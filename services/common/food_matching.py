"""Fail-closed identity checks: a valid catalogue ID alone is not a food match."""
import json
import re
import unicodedata
from functools import lru_cache

from services.common.meal_engine import DATA, ExtractedItem, catalogue, evaluate


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
_MASS = _NUMBER + (
    r'\s*(?:千克|公斤|kg|grams?|克|g|斤|(?:小|大)?(?:碗|盘|盤|碟)|'
    r'块|塊|个|個|人?份|杯)')
_SPLIT = re.compile(
    r'[,，;；。\n、]|(?<!\d)\.(?=\s|$)|\b(?:and|plus)\b|以及|还有|還有|另外|和', re.I)
_PREFIX = re.compile(
    r'(?:\s|[:：]|' + _MASS + r'|'
    r'我|今天|早餐|午餐|晚餐|午饭|晚饭|另吃了|另吃|吃了|吃的|吃|有|一份|一碗|两个|兩個|'
    r'请估算|估算|请计算|计算|去壳|去殼|去骨|净重|淨重|的|'
    r'(?<![a-z])(?:i ate|i had|i have|for lunch|for dinner|for breakfast|'
    r'a serving of|one serving of|a portion of|one bowl of|a bowl of|'
    r'of the chinese dish|of|the|some)(?![a-z]))+',
    re.I,
)
_SUFFIX = re.compile(
    r'(?:\s|[.。:：()]|' + _MASS + r'|'
    r'熟重|生重|可食部分|净重|淨重|已去壳|已去殼|已去骨|'
    r'(?:去壳|去殼|去骨)(?:后|後)?|共|总共|總共|的|少油|多油|不加油|'
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
            r'(?:实际|實際|另吃了|另吃|吃了|吃下|可食部分|还是|還是|仍是|是|为|為|共|总共|'
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
    if re.fullmatch(
            r'(?:也)?(?:没有|沒有|没|沒|无|無|未)(?:额外|額外)?(?:添加|加|用)?'
            r'(?:任何)?(?:(?:其他|其它)?油|香油|芝麻油|花生油|菜籽油|橄榄油|橄欖油|食用油)', value):
        return True
    # Complete measurement/preparation sentences are not additional foods.
    # Keep the grammar closed: arbitrary nouns or appended dishes must still
    # reach the coverage guard, even when they follow one of these phrases.
    if re.fullmatch(
            r'(?:(?:称|稱)(?:的)?(?:是|为|為)|(?:重量|称重|稱重)(?:是|为|為))?'
            r'(?:(?:炒熟|煮熟|蒸熟|烤熟|做熟|熟制|烹调|烹調)(?:后|後)(?:的)?)?'
            r'(?:(?:本次|这次|這次)?(?:实际|實際)?(?:吃下|吃了)(?:的)?)?'
            r'(?:熟重|生重|可食(?:重量|净重|淨重)|可食部分(?:的重量)?|净重|淨重)', value):
        return True
    if re.fullmatch(r'(?:没有|沒有|没|沒)(?:称重|稱重)', value):
        return True
    if re.fullmatch(r'(?:刚才|剛才)?(?:份量|分量|重量)(?:记错了|記錯了)', value):
        return True
    if re.fullmatch(r'配方(?:及其他(?:资料|資料))?(?:都)?(?:不变|不變)', value):
        return True
    if re.fullmatch(
            r'(?:实际|實際)(?:吃了|吃下)\s*' + _MASS +
            r'(?:熟食)?(?:净重|淨重|可食净重|可食淨重)', value, re.I):
        return True
    if re.fullmatch(r'熟(?:鱼肉|魚肉)(?:净重|淨重|可食重量)', value):
        return True
    if re.fullmatch(
            r'(?:都)?是(?:实际|實際)(?:吃下|吃了)的熟食(?:净重|淨重)|'
            r'(?:都)?是(?:炒熟|煮熟|蒸熟|烤熟|做熟)(?:后|後)(?:吃下|吃了)的重量', value):
        return True
    if re.fullmatch(
            r'(?:都)?(?:已经|已經|已)?(?:炒熟|煮熟|蒸熟|烤熟|做熟)(?:了)?', value):
        return True
    if re.fullmatch(
            r'(?:没有|沒有|无|無)(?:骨头|骨頭|鱼骨|魚骨)|'
            r'(?:骨头|骨頭|鱼骨|魚骨)(?:没有|沒有|没|沒)(?:吃|吃下)', value):
        return True
    if re.fullmatch(r'(?:大概|大约|大約|约|約)\s*' + _MASS, value, re.I):
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


_NUMERIC_MASS = re.compile(
    r'(?<![\d.+-])\d+(?:\.\d+)?\s*(?:千克|公斤|kg|grams?|克|g|斤)(?![a-z])',
    re.I,
)


def _quantity_led_chunks(text):
    """Recognize adjacent quantity-led items without splitting food-name words.

    This is only a grounding fallback, not an input rewrite or a quantity parser.
    Keep original text for whole-meal coverage, recipe facts and corrections.
    Numeric mass units delimit these lists; portion words such as 三杯 must not
    split a dish name like 三杯鸡. A trailing weight/detail is not a new item.
    """
    amounts = list(_NUMERIC_MASS.finditer(text))
    if len(amounts) < 2 or not _wrapper(
            _SPLIT.split(text[:amounts[0].start()])[-1], _PREFIX):
        return []
    ends = [amount.start() for amount in amounts[1:]] + [len(text)]
    if any(_detail_clause(text[amount.end():end])
           for amount, end in zip(amounts, ends)):
        return []
    starts = [0] + [amount.start() for amount in amounts[1:]]
    return [text[start:end] for start, end in zip(starts, ends)]


def _wrapped_mention(needle, text):
    for match in re.finditer(re.escape(needle), text):
        left = _SPLIT.split(text[:match.start()])[-1]
        right = _SPLIT.split(text[match.end():])[0]
        if _wrapper(left, _PREFIX) and _detail_clause(right):
            return True
    return False


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
        if _wrapped_mention(needle, text):
            return True
        if any(_wrapped_mention(needle, chunk) for chunk in _quantity_led_chunks(text)):
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
        exclusive_meal = re.fullmatch(
            r'\s*(?:更正\s*[:：]\s*)?'
            r'(?:(?:不要|没吃|沒吃|没有吃|沒有吃)[^,，;；。\n]+[,，;；]\s*)?'
            r'(?:(?:我)?(?:这餐|這餐|这次|這次)|我)?'
            r'只吃(?:下)?了\s*(.+)', text, re.S,
        )
        if exclusive_meal and any(
                not _detail_clause(clause) for clause in _SPLIT.split(exclusive_meal[1])):
            # "Only ate" explicitly replaces the meal; keep its entire list and
            # all later additions. Never infer replacement from a negation alone
            # or from a quantity-only update with no new food identity.
            return [exclusive_meal[1], *texts[index + 1:]]
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


def current_identity_texts(food_text, history=None):
    """Share explicit replacement scope between model context and final grounding."""
    return _current_identity_texts(user_texts(food_text, history))


_ACKNOWLEDGMENT = re.compile(
    r'(?:是|是的|对|對|对的|對的|没错|沒錯|正确|正確|确认|確認|不是|不对|不對|'
    r'yes|no|correct|that[’\']s right)[.!。！]?', re.I,
)
_DETAIL_QUESTION = re.compile(
    r'(?:(?:请问|請問|请确认|請確認|请确认一下|請確認一下|是否|是|这是|這是|'
    r'这个重量是|這個重量是|重量是)\s*)*'
    r'(?:(?:去壳|去殼|去骨)(?:后|後)?的?)?'
    r'(?:熟重|生重|可食重量|可食部分的重量)(?:吗|嗎|么|麼)?[?？。]?|'
    r'(?:is (?:this|that|it) (?:the )?|please confirm (?:the )?)'
    r'(?:cooked edible weight|raw edible weight|edible weight|cooked weight|raw weight)'
    r'[?.]?', re.I,
)



def _is_user_bound_weight_question(content, verified, prior_users):
    # Apply the same explicit-replacement scope as final grounding. A prior
    # "change to rice" is user naming evidence for rice, not an assistant suggestion.
    prior_scope = _current_identity_texts(prior_users)
    bound = [item for item in verified if is_user_mention(item.source_text, prior_scope)]
    if not bound:
        return False
    if _DETAIL_QUESTION.fullmatch(content):
        return True
    # Recognize the exact current server-generated question, including its
    # canonical food label and explanation. Do not strip arbitrary food prefixes
    # or accept a combined recipe/multiple-question prompt as one confirmation.
    pending = [{**item.model_dump(), 'weight_basis': None} for item in bound]
    return any(question['key'].endswith('.weight_basis') and content == question['label']
               for question in evaluate(pending)['questions'])

def _detail_acknowledgments(food_text, history, verified):
    """Exclude only standalone replies to a bounded weight clarification.

    An assistant message cannot introduce a food identity. The food must already
    be present in user text before the question; additions and arbitrary replies
    still pass through the complete-meal coverage guard below.
    """
    entries = list(history or [])
    if not entries or entries[-1].get('role') != 'user' or entries[-1].get('content') != food_text:
        entries.append({'role': 'user', 'content': food_text})
    accepted = set()
    prior_users = [] if _ACKNOWLEDGMENT.fullmatch(food_text.strip()) else [food_text]
    for index, entry in enumerate(entries):
        if entry.get('role') != 'user':
            continue
        content = entry.get('content', '').strip()
        previous = entries[index - 1] if index else {}
        if (_ACKNOWLEDGMENT.fullmatch(content)
                and previous.get('role') == 'assistant'
                and _is_user_bound_weight_question(
                    previous.get('content', '').strip(), verified, prior_users)):
            accepted.add(content)
        prior_users.append(content)
    return accepted


def ground_food_items(items, food_text, history=None):
    """Clear unverified IDs before any mode-specific nutrient assumptions.

    Qwen must copy the original whole food mention in source_text. For older
    responses, the unchanged name can provide the same evidence. A unique exact
    reviewed name match determines identity, independently of Qwen's guessed ID.
    """
    texts = current_identity_texts(food_text, history)
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
        acknowledgments = _detail_acknowledgments(food_text, history, verified)
        for text in texts:
            if text.strip() in acknowledgments:
                continue
            remaining = unicodedata.normalize('NFKC', text).casefold()
            for item in verified:
                remaining = remaining.replace(
                    unicodedata.normalize('NFKC', item.source_text).casefold(), '')
            for clause in _SPLIT.split(remaining):
                clause = clause.strip(' .。:：')
                if not _detail_clause(clause):
                    items.append(ExtractedItem(name=clause[:120], source_text=clause[:120]))
    return items
