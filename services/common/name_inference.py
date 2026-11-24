"""Conservative dish-name evidence for editable recipe-reference guesses.

This vocabulary never authorizes an exact food identity. Unknown words, missing
main ingredients and implicit cooking methods require user clarification instead
of silently choosing a supported substitute. Reference quantities still need review.
"""
import re
import unicodedata
from functools import lru_cache

from services.common.food_matching import matching_aliases
from services.common.meal_engine import catalogue
from services.common.preparations import recognized_preparations


# Short culinary nouns omitted by the source's detailed ingredient labels. Do not
# generalize a cut/species record to all meat, fish or mushrooms of that family.
_NOUNS = {
    '豆腐': {'tofu', 'tofu_soft'}, 'tofu': {'tofu', 'tofu_soft'},
    '硬豆腐': {'tofu'}, '老豆腐': {'tofu'}, '嫩豆腐': {'tofu_soft'},
    '软豆腐': {'tofu_soft'}, '雞蛋': {'egg_raw'}, '鸡蛋': {'egg_raw'},
    'egg': {'egg_raw'}, 'eggs': {'egg_raw'}, 'eggplant': {'eggplant'},
    'aubergine': {'eggplant'}, '虾仁': {'shrimp'}, '蝦仁': {'shrimp'},
    'peeled shrimp': {'shrimp'}, 'shrimp': {'shrimp'}, 'broccoli': {'broccoli'},
    'asparagus': {'asparagus'}, '花生': {'peanut'}, 'peanuts': {'peanut'},
    'peanut': {'peanut'}, '黄瓜': {'cucumber'}, '黃瓜': {'cucumber'},
    'cucumber': {'cucumber'}, '土豆': {'potato'}, 'potato': {'potato'},
    'potatoes': {'potato'}, '牛肉块': {'beef_chunk'}, '牛肉塊': {'beef_chunk'},
    '牛肉末': {'beef'}, 'ground beef': {'beef'}, 'minced beef': {'beef'},
    '猪肉末': {'pork_ground'}, '豬肉末': {'pork_ground'},
    '鸡胸肉': {'chicken'}, '雞胸肉': {'chicken'}, 'chicken breast': {'chicken'},
    '鸡腿肉': {'chicken_thigh'}, '雞腿肉': {'chicken_thigh'},
    'chicken thigh': {'chicken_thigh'},
}

# Closed culinary grammar: meaningful leftover words are a reason to ask, not
# permission to drop an unsupported ingredient. No blanket "meat"/"fish" token.
_DESCRIPTORS = (
    '家常', '自制', '手工', '清蒸', '清炒', '清炖', '红烧', '紅燒',
    '蒜香', '蒜蓉', '葱香', '葱烧', '姜葱', '薑蔥', '酱烧', '醬燒',
    '鱼香', '魚香', '蚝油', '蠔油', '豉油', '酱油', '醬油', '椒盐', '椒鹽',
    '香辣', '麻辣', '酸辣', '甜辣', '糖醋', '黑椒', '白灼', '干锅', '乾鍋',
    '少油', '少盐', '少鹽', '原味', '清淡', '凉拌', '涼拌', '冷拌',
    '油炸', '煎炸', '油煎', '香煎', '生煎', '烧烤', '燒烤', '炖煮', '燉煮',
    '煸炒', '拌匀', '拌勻', '煮', '焯', '汆', '氽', '蒸', '烤', '焗', '炒',
    '煎', '炸', '炖', '燉', '焖', '燜', '卤', '滷', '烧', '燒', '拌',
    '汤', '湯', '煲', '羹', '块', '塊', '粒', '丁', '丝', '絲', '片',
    '和', '与', '與', '配', '加', '的',
    'stir-fried', 'stir fried', 'pan-fried', 'pan fried', 'deep-fried', 'deep fried',
    'cold tossed', 'boiled', 'blanched', 'poached', 'steamed', 'roasted', 'baked',
    'grilled', 'braised', 'stewed', 'fried', 'raw', 'salad', 'soup', 'stew',
    'garlic', 'spicy', 'home-style', 'homestyle', 'homemade', 'sauce',
    'with', 'and', 'in', 'of', 'a', 'the', 'diced', 'sliced', 'shredded',
)
_NEGATION = re.compile(
    r'不含|不加|不用|没有|沒有|无|無|未|不要|(?<![a-z])(?:no|not|without|non)(?![a-z])',
    re.I,
)


def _text(value):
    return unicodedata.normalize('NFKC', value).casefold()


def _pattern(phrase):
    phrase = _text(phrase)
    value = re.escape(phrase).replace(r'\ ', r'\s+')
    # English fragments must not match substrings such as ham in champagne.
    return re.compile((r'(?<![a-z])' if phrase[:1].isascii() and phrase[:1].isalpha()
                       else '') + value +
                      (r'(?![a-z])' if phrase[-1:].isascii() and phrase[-1:].isalpha()
                       else ''))


@lru_cache(maxsize=1)
def _ingredient_terms():
    terms = {}
    for food in catalogue()['foods']:
        if food['kind'] != 'ingredient':
            continue
        aliases = [food['name'], *food['aliases'], *matching_aliases().get(food['id'], [])]
        for alias in aliases:
            label = re.split(r'[（(]', alias)[0].strip()
            # Remove one state prefix, never a cut, species, skin or firmness.
            short = re.sub(r'^(?:冷冻生|冷凍生|生鲜|生鮮|鲜|鮮|生|干|乾)', '', label)
            short = re.sub(r'^(?:raw|fresh|dried)\s+', '', short, flags=re.I)
            for term in (label, short):
                if len(term) >= 2:
                    terms.setdefault(_text(term), set()).add(food['id'])
    for term, ids in _NOUNS.items():
        terms.setdefault(_text(term), set()).update(ids)
    return [(term, _pattern(term), ids) for term, ids in
            sorted(terms.items(), key=lambda pair: -len(pair[0]))]


def _mentions(name):
    """Keep longest ingredient spans; seasoning compounds cannot license mains."""
    occupied = set()
    mentions = []
    for term, pattern, ids in _ingredient_terms():
        for match in pattern.finditer(name):
            # In "pan-fried tofu", fried belongs to the compound cooking verb,
            # not an explicit declaration of the pre-fried ingredient record.
            if term.startswith('fried ') and re.search(
                    r'\b(?:pan|deep|stir)[-\s]+$', name[:match.start()]):
                continue
            span = set(range(match.start(), match.end()))
            if span & occupied:
                continue
            occupied |= span
            mentions.append(ids)
    remainder = ''.join(' ' if i in occupied else char for i, char in enumerate(name))
    for phrase in sorted(_DESCRIPTORS, key=len, reverse=True):
        remainder = _pattern(phrase).sub(' ', remainder)
    return mentions, re.sub(r'[\W_]+', '', remainder)


def clarification(provider, zh, en):
    return {'provider': provider, 'status': 'needs_clarification', 'ingredient_ids': [],
            'preparation': None, 'reason_zh': zh, 'reason_en': en}


def grounded_inference(value, original_name, seasonings):
    """Downgrade semantic uncertainty; never repair it by replacing food IDs."""
    if value['status'] != 'suggested':
        return value
    name = _text(original_name)
    provider = value['provider']
    if _NEGATION.search(name):
        return clarification(provider,
            '菜名包含排除或否定信息。实际包含哪些主要食材，采用什么做法？请在下方选择。',
            'The name includes an exclusion. Which main ingredients and cooking method '
            'were actually used? Select them below.')
    mentions, remainder = _mentions(name)
    mains = set(value['ingredient_ids']) - seasonings
    named_mains = [ids - seasonings for ids in mentions if ids - seasonings]
    allowed = set().union(*named_mains) if named_mains else set()
    if remainder or not named_mains:
        return clarification(provider,
            '仅凭菜名无法确认全部食材，或目录缺少对应种类。实际用了哪些主要食材、部位及做法？'
            '请在下方核对选择；没有对应记录时不以其他食材替代。',
            'The name does not establish all ingredients, or the exact type is unsupported. '
            'Which ingredients, cuts and method were used? Select them below; '
            'do not substitute another ingredient for an unsupported one.')
    if mains - allowed or any(len(ids & mains) != 1 for ids in named_mains):
        return clarification(provider,
            '推测的主要食材与菜名不一致，未采用这组推测。实际有哪些食材、部位，是否另加肉类？'
            '请在下方选择全部主要食材和做法。',
            'The proposed main ingredients do not match the name, so they were discarded. '
            'Which ingredients and cuts were used, including any added meat? '
            'Select all actual main ingredients and the method below.')
    methods = recognized_preparations(name)
    if len(methods) != 1 or value['preparation'] not in methods:
        return clarification(provider,
            '菜名未明确唯一做法，或推测做法与菜名不符。实际是炒、煎炸、蒸、炖烧、煮、烤还是凉拌？'
            '请在下方选择做法并核对主要食材。',
            'The name does not establish one compatible cooking method. Was it stir-fried, '
            'fried, steamed, braised, boiled, roasted or cold tossed? '
            'Select the actual method and main ingredients below.')
    # Display facts, not unvalidated culinary claims or hidden model assumptions.
    return {**value,
            'reason_zh': '这是根据菜名提出的食材和做法建议，尚未确认实际配方；'
                         '请核对下方具体食材种类、状态和做法。',
            'reason_en': 'These ingredients and preparation are suggestions based on the name, '
                         'not a verified recipe. Review the exact ingredient types, states '
                         'and method below.'}
