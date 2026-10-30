"""Rebuild curated CC0 nutrients from the official SR Legacy CSV zip (offline input)."""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import zipfile

DATA = Path(__file__).resolve().parents[1] / 'services/common/data'
SOURCE = 'https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip'
VERSION = '2026-10-31.1'


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
