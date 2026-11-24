"""Conservative cooking-verb evidence shared by names and recipe descriptions."""
import re


# Normalize only characters used by the cooking and negation vocabulary.
# Character-for-character translation preserves the positions returned below.
_COOKING_SCRIPT_TRANSLATION = str.maketrans(
    '燉燜滷紅燒開涼過無採經沒預進與處乾淺賣麥須製',
    '炖焖卤红烧开凉过无采经没预进与处干浅卖麦须制')
_PREPARATION_PATTERN = re.compile('|'.join(
    f'(?P<{preparation}>{pattern})' for preparation, pattern in {
        'raw': r'生食|生吃|\braw\b',
        'as_served': r'凉拌|冷拌|糖拌|拌|\b(?:cold[-\s]+tossed|salad)\b',
        'boiled': r'烧开|烧沸|煮|焯|汆|氽|熬粥|白灼|\b(?:boiled|blanched|poached)\b',
        'steamed': r'蒸|\bsteamed\b',
        'roasted': r'烧烤|烤|焗|\b(?:roasted|baked|grilled)\b',
        'stir_fried': r'炒|\bstir[-\s]+fried\b',
        'fried': r'煎|炸|过油|\b(?:(?:pan|deep)[-\s]+)?fried\b',
        'braised': r'炖|焖|卤|红烧|烧制|(?<!叉|照)烧(?!烤|卖|麦|开|沸)|\b(?:braised|stewed)\b',
    }.items()), re.IGNORECASE)
_NEGATED_PREFIX = re.compile(
    r'(?:不是|不等同|不采用|不使用|无需|无须|不需要|不需|不用|不经|未经|没有|不含|非|未|不|免|无)'
    r'(?:再|先|预先|提前|进行|经过|采用|使用|用|经|需|需要|油|水|干|深|浅)*$')
_NEGATED_CONTINUATION = re.compile(
    r'(?:制|熟|版|处理)?(?:、|及|或|与|和|/|以及)?(?:油|水|干|深|浅)?')
_ENGLISH_NEGATED_PREFIX = re.compile(
    r'\b(?:not|no|never|without|non)(?:\s+(?:been|being|previously))?[-\s]*$',
    re.IGNORECASE)
_ENGLISH_NEGATED_CONTINUATION = re.compile(r'\s*(?:and|or|/)\s*', re.IGNORECASE)


def preparation_steps(text):
    """Return explicit, non-negated cooking verbs in their described order.

    Negation covers adjacent/coordinated verbs (e.g. 不煎炸 / 不煎或炸),
    but stops at a new step or clause. Dish types such as 汤 and 煲 alone
    do not establish a preparation.
    """
    text = text.translate(_COOKING_SCRIPT_TRANSLATION)
    steps = []
    previous_end, previous_negated = 0, False
    for match in _PREPARATION_PATTERN.finditer(text):
        prefix = text[previous_end:match.start()]
        compact_prefix = re.sub(r'\s+', '', prefix)
        negated = bool(_NEGATED_PREFIX.search(compact_prefix)
                       or _ENGLISH_NEGATED_PREFIX.search(prefix)) or (
            previous_negated and (
                (not match.group().isascii()
                 and _NEGATED_CONTINUATION.fullmatch(compact_prefix) is not None)
                or _ENGLISH_NEGATED_CONTINUATION.fullmatch(prefix) is not None))
        if not negated:
            steps.append((match.lastgroup, match.start()))
        previous_end, previous_negated = match.end(), negated
    return steps


def recognized_preparations(text):
    """Return preparations evidenced by explicit, non-negated cooking verbs."""
    return {preparation for preparation, _ in preparation_steps(text)}
