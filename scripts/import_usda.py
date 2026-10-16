"""Rebuild curated CC0 nutrients from the official SR Legacy CSV zip (offline input)."""
import argparse
import csv
import io
import json
from pathlib import Path
import zipfile

DATA = Path(__file__).resolve().parents[1] / 'services/common/data'
SOURCE = 'https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip'


def build(path):
    selected = json.loads((DATA / 'usda_selection.json').read_text())
    by_id = {str(f['fdc_id']): f for f in selected}
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
    (DATA/'catalogue.json').write_text(json.dumps(dict(version='2026-10-16.1',
        foods=result+recipes), ensure_ascii=False, indent=2)+'\n')
    print(f'Imported {len(result)} ingredients and {len(recipes)} recipes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('zip_path', help='Official SR Legacy CSV zip; no API key required')
    build(parser.parse_args().zip_path)
