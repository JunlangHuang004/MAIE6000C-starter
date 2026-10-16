"""Strict parser and approximate demo catalogue; no unknown-food guessing."""
import re
from decimal import Decimal, ROUND_HALF_UP

NUTRITION_PER_100G = {
    "chicken breast": (165.0, 31.0, 0.0, 3.6),
    "white rice": (130.0, 2.7, 28.0, 0.3),
    "rice": (130.0, 2.7, 28.0, 0.3),
    "egg": (155.0, 13.0, 1.1, 11.0),
    "salmon": (208.0, 20.0, 0.0, 13.0),
    "broccoli": (35.0, 2.4, 7.2, 0.4),
}
FOODS = "|".join(re.escape(name) for name in sorted(NUTRITION_PER_100G, key=len, reverse=True))
ITEM = re.compile(
    rf"(?P<grams>\d+(?:\.\d+)?)\s*(?:grams?|g)\s+(?:cooked\s+)?(?P<food>{FOODS})",
    re.IGNORECASE,
)


def parse_meal(text: str) -> list[tuple[str, Decimal]]:
    parts = re.split(r"\s*(?:,|;|\band\b|\+)\s*", text.strip(), flags=re.IGNORECASE)
    items = []
    for part in parts:
        match = ITEM.fullmatch(part.strip())
        if match is None:
            raise ValueError(
                "Use supported foods with grams, e.g. 200g chicken breast and 230g white rice. "
                "Separate items with and, commas, semicolons or +."
            )
        grams = Decimal(match['grams'])
        if not 0 < grams <= 10000:
            raise ValueError("Each food weight must be greater than 0 and at most 10000 grams.")
        items.append((match['food'].lower(), grams))
    return items


def estimate_meal(text: str) -> dict[str, float]:
    totals = [Decimal(0)] * 4
    for food, grams in parse_meal(text):
        for index, nutrient in enumerate(NUTRITION_PER_100G[food]):
            totals[index] += Decimal(str(nutrient)) * grams / 100
    return {
        key: float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        for key, value in zip(("calories", "protein_g", "carbs_g", "fat_g"), totals)
    }
