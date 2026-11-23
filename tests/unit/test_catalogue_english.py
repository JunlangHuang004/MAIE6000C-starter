"""English UI labels must identify the same reviewed foods in extraction."""
import json
from pathlib import Path

import pytest

from services.common.catalogue_search import catalogue_candidates
from services.common.food_matching import ground_food_items, name_index, normalize_name
from services.common.meal_engine import ExtractedItem, catalogue


ROOT = Path(__file__).resolve().parents[2]
LABEL_SOURCE = (ROOT / 'services/api/app/static/catalogue-en.js').read_text()
LABELS = json.loads(LABEL_SOURCE.split('Object.freeze(', 1)[1].rsplit(');', 1)[0])
FOODS = catalogue()['foods']


def test_english_labels_cover_exactly_current_catalogue_ids():
    assert set(LABELS) == {food['id'] for food in FOODS}


@pytest.mark.parametrize('food', FOODS, ids=lambda food: food['id'])
def test_each_english_display_name_retrieves_and_grounds_its_own_record(food):
    name = LABELS[food['id']]['name']
    assert name_index()[normalize_name(name)] == {food['id']}
    text = '100g ' + name
    assert food['id'] in {row['id'] for row in catalogue_candidates(text)}
    items = ground_food_items([ExtractedItem(name=name, source_text=name, food_id='rice',
                                            grams=100)], text)
    assert len(items) == 1
    assert items[0].food_id == food['id']
    assert items[0].grams == 100
