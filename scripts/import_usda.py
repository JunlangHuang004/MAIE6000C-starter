"""Rebuild USDA ingredients and retain attributed prepared-food references (offline input)."""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import zipfile

DATA = Path(__file__).resolve().parents[1] / 'services/common/data'
SOURCE = 'https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip'
VERSION = '2026-11-24.1'
CFS_WORKBOOK_URL = 'https://www.cfs.gov.hk/resources/Nutrient%20profiles_FRL.xlsx'
CFS_REFERENCE_ROWS = {
    'dish_004': 351, 'dish_007': 350, 'dish_012': 333, 'dish_064': 375,
    'dish_110': 346, 'dish_202': 343, 'dish_266': 339, 'dish_269': 355,
    'dish_339': 386, 'dish_341': 471,
}
PREPARED_REFERENCE_PREPARATIONS = {
    'as_served', 'boiled', 'steamed', 'roasted', 'stir_fried', 'fried', 'braised',
}
CFS_REFERENCE_PREPARATIONS = {
    'dish_004': {'as_served', 'braised'}, 'dish_007': {'as_served', 'stir_fried'},
    'dish_012': {'as_served', 'stir_fried'}, 'dish_064': {'as_served'},
    'dish_110': {'as_served', 'steamed'}, 'dish_202': {'as_served', 'braised'},
    'dish_266': {'as_served'}, 'dish_269': {'as_served', 'fried'},
    'dish_339': {'as_served', 'stir_fried'}, 'dish_341': {'as_served'},
}


def validate_measured_reference(food):
    """Keep the reviewed CFS subset distinct from recipe and USDA carbohydrate data."""
    if 'measured_reference' not in food:
        return
    reference = food['measured_reference']
    row = CFS_REFERENCE_ROWS.get(food['id'])

    def fail():
        raise ValueError(f'Invalid measured reference: {food["id"]}')

    def number(value, *, positive=False):
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value) and (value > 0 if positive else value >= 0))

    if (food.get('kind') != 'recipe' or not row or not isinstance(reference, dict)
            or reference.get('id') != f'cfs_frl_eng_{row}'
            or reference.get('version') != '2026-10-02'
            or reference.get('nutrition_basis') != 'per_100g_cooked_edible'
            or reference.get('carbohydrate_basis') != 'available'
            or reference.get('match_scope') != 'same_named_prepared_dish'):
        fail()
    preparations = reference.get('compatible_preparations')
    if (not isinstance(preparations, list) or not preparations
            or not all(isinstance(value, str) for value in preparations)
            or len(preparations) != len(set(preparations))
            or 'as_served' not in preparations
            or set(preparations) - PREPARED_REFERENCE_PREPARATIONS
            or set(preparations) != CFS_REFERENCE_PREPARATIONS[food['id']]):
        fail()
    nutrients = reference.get('nutrients')
    if (not isinstance(nutrients, dict)
            or set(nutrients) != {'calories', 'protein_g', 'fat_g', 'carbs_g'}
            or not all(number(value) for value in nutrients.values())
            or not number(nutrients['calories'], positive=True)
            or nutrients['calories'] > 1000
            or sum(nutrients[key] for key in ('protein_g', 'fat_g', 'carbs_g')) > 100):
        fail()
    source = reference.get('source')
    if (not isinstance(source, dict) or source.get('id') != f'CFS-FRL-Eng-{row}'
            or source.get('url') != CFS_WORKBOOK_URL
            or not all(isinstance(source.get(key), str) and source[key].strip()
                       for key in ('name', 'license'))
            or source.get('license') != 'No open licence asserted; CFS copyright notice applies'
            or source.get('rights_url') != 'https://www.cfs.gov.hk/english/notices/notices.html'):
        fail()
    if (not all(isinstance(reference.get(key), str) and reference[key].strip()
                for key in ('source_name_zh', 'source_name_en', 'notes_zh', 'notes_en',
                            'preparation_notes_zh', 'preparation_notes_en'))
            or reference.get('source_workbook_sheet') != 'Eng'
            or reference.get('source_workbook_range') != f'C{row}:I{row}'
            or reference.get('source_workbook_sha256') != (
                '75c77d304a3d2199a1bac3326e9e0458e798f5519e569f4422556b3104ec475d')
            or reference.get('source_workbook_last_modified') != '2026-10-02T08:00:51Z'
            or reference.get('retrieved_at') != '2026-11-24'):
        fail()
    fibre = reference.get('dietary_fibre')
    if not isinstance(fibre, dict) or not (
            (set(fibre) == {'value_g'} and number(fibre['value_g']) and fibre['value_g'] <= 100)
            or fibre == {'qualifier': 'trace'}):
        fail()
    ranges = reference.get('observed_ranges')
    if ranges is not None:
        if (food['id'] not in {'dish_012', 'dish_266'} or not isinstance(ranges, dict)
                or set(ranges) != {'calories', 'fat_g'} or reference.get('sample_count') != 10
                or reference.get('sample_collection_period') != '2017-03/2017-04'
                or reference.get('range_source_url') != (
                    'https://www.cfs.gov.hk/english/programme/programme_rafs/'
                    'programme_rafs_n_01_23_abstract.html')):
            fail()
        for key, bounds in ranges.items():
            if (not isinstance(bounds, dict) or set(bounds) != {'min', 'max'}
                    or not all(number(value) for value in bounds.values())
                    or not bounds['min'] <= nutrients[key] <= bounds['max']):
                fail()
    elif any(key in reference for key in (
            'sample_count', 'sample_collection_period', 'range_source_url')):
        fail()


def validate_catalogue(foods):
    """Reject broken references or ambiguous dish aliases before publishing the snapshot."""
    ids = [food['id'] for food in foods]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate food IDs')
    ingredients = {food['id'] for food in foods if food['kind'] == 'ingredient'}
    recipe_aliases = {}

    def weight(value, *, positive=False):
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value) and (0 < value if positive else 0 <= value)
                and value <= 10000)

    for food in foods:
        validate_measured_reference(food)
        if food['kind'] == 'ingredient':
            expected = {'calories', 'protein_g', 'fat_g', 'carbs_g'}
            if set(food['nutrients']) != expected or not all(
                    weight(value) for value in food['nutrients'].values()):
                raise ValueError(f'Invalid nutrients: {food["id"]}')
            continue
        if food['kind'] != 'recipe':
            raise ValueError(f'Invalid food kind: {food["id"]}')
        recipe = food['recipe']
        amounts = recipe['ingredients']
        if not amounts or set(amounts) - ingredients:
            raise ValueError(f'Unknown or non-ingredient recipe reference: {food["id"]}')
        if (not weight(recipe['yield_g'], positive=True)
                or not all(weight(value) for value in amounts.values())
                or not any(value > 0 for value in amounts.values())):
            raise ValueError(f'Invalid recipe weights: {food["id"]}')
        portions = food.get('portion_weights_g', {})
        if (set(portions) - {'bowl', 'piece', 'cup', 'serving'}
                or not all(weight(value, positive=True) for value in portions.values())
                or not weight(food.get('default_portion_g', 200), positive=True)):
            raise ValueError(f'Invalid reference portions: {food["id"]}')
        for alias in {food['name'], *food.get('aliases', [])}:
            key = alias.strip().casefold()
            if not key or (key in recipe_aliases and recipe_aliases[key] != food['id']):
                raise ValueError(f'Duplicate or empty dish alias: {alias}')
            recipe_aliases[key] = food['id']


def build(path):
    selected = json.loads((DATA / 'usda_selection.json').read_text())
    by_id = {str(f['fdc_id']): f for f in selected}
    if len(by_id) != len(selected):
        raise ValueError('Duplicate FDC selection IDs; do not silently discard records')
    with zipfile.ZipFile(path) as archive:
        def rows(name):
            member = next(n for n in archive.namelist() if n.split('/')[-1] == name)
            return csv.DictReader(io.TextIOWrapper(archive.open(member), encoding='utf-8-sig'))
        descriptions = {r['fdc_id']:r['description'] for r in rows('food.csv')}
        values = {fid:{} for fid in by_id}
        nutrients = {'1008':'calories', '1003':'protein_g', '1004':'fat_g', '1005':'carbs_g'}
        for row in rows('food_nutrient.csv'):
            if row['fdc_id'] in by_id and row['nutrient_id'] in nutrients and row['amount']:
                values[row['fdc_id']][nutrients[row['nutrient_id']]] = float(row['amount'])
    result = []
    for fid, food in by_id.items():
        if len(values[fid]) != 4:
            raise ValueError(f'Missing nutrients for {fid}; never replace missing values with zero')
        result.append(dict(**food, kind='ingredient',
            nutrients=values[fid], nutrition_basis='per_100g_edible',
            source=dict(name='USDA FoodData Central SR Legacy 2018', license='CC0-1.0',
                id=fid, url=f'https://fdc.nal.usda.gov/food-details/{fid}/nutrients',
                description=descriptions[fid], download=SOURCE)))
    recipe_path = DATA / 'recipes.json'
    recipes = json.loads(recipe_path.read_text()) if recipe_path.exists() else []
    validate_catalogue(result + recipes)
    (DATA/'catalogue.json').write_text(json.dumps(dict(version=VERSION,
        foods=result+recipes), ensure_ascii=False, indent=2)+'\n')
    print(f'Imported {len(result)} ingredients and {len(recipes)} recipes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('zip_path', help='Official SR Legacy CSV zip; no API key required')
    build(parser.parse_args().zip_path)
