"""Keep reported carbohydrate definitions distinct in durable nutrition details."""
import math


CARBOHYDRATE_BASES = frozenset({'available', 'total_by_difference'})
NUTRIENT_KEYS = ('calories', 'protein_g', 'carbs_g', 'fat_g')


def valid_nutrient(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and value >= 0)


def carbohydrate_summary(details):
    """Read snapshots only; pre-reference records used USDA total carbohydrate."""
    if not details:
        return None
    amounts = {}
    for detail in details:
        basis = detail.get('carbohydrate_basis', 'total_by_difference')
        value = detail.get('nutrients', {}).get('carbs_g')
        if basis not in CARBOHYDRATE_BASES or not valid_nutrient(value):
            return None
        amounts[basis] = amounts.get(basis, 0.0) + value
    return {
        'basis': 'mixed' if len(amounts) > 1 else next(iter(amounts)),
        'available_g': round(amounts['available'], 1) if 'available' in amounts else None,
        'total_by_difference_g': (round(amounts['total_by_difference'], 1)
                                  if 'total_by_difference' in amounts else None),
    }


def complete_mixed_details(details, draft, totals):
    """Allow a missing combined carbohydrate total only for complete mixed evidence."""
    summary = carbohydrate_summary(details)
    if not summary or summary['basis'] != 'mixed' or len(details) != len(draft):
        return False
    if {detail.get('item_index') for detail in details} != set(range(len(draft))):
        return False
    for detail in details:
        # The exception requires the new explicit definitions, not inferred legacy ones.
        if detail.get('carbohydrate_basis') not in CARBOHYDRATE_BASES:
            return False
        nutrients = detail.get('nutrients', {})
        if set(nutrients) != set(NUTRIENT_KEYS) or not all(
                valid_nutrient(nutrients[key]) for key in NUTRIENT_KEYS):
            return False
    # Details and totals are independently rounded once to one decimal place.
    tolerance = 0.05 * (len(details) + 1) + 1e-9
    return all(valid_nutrient(totals[key]) and abs(
        totals[key] - sum(detail['nutrients'][key] for detail in details)) <= tolerance
        for key in ('calories', 'protein_g', 'fat_g'))
