"""Check selected CFS facts, nutrient definitions and reproducible offline ingestion."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import zipfile

import pytest

from scripts import import_usda as importer


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = json.loads((importer.DATA / 'catalogue.json').read_text())
RECIPES = json.loads((importer.DATA / 'recipes.json').read_text())
MANIFEST = json.loads((ROOT / 'docs/evidence/cfs-prepared-food-source-map.json').read_text())
BY_ID = {food['id']: food for food in SNAPSHOT['foods']}
# Independently transcribed selected cells: row, kcal, protein, fat, available carbohydrate.
EXPECTED = {
    'dish_004': (351, 130, 7.5, 9.2, 3.7),
    'dish_007': (350, 200, 8, 17, 4),
    'dish_012': (333, 230, 13, 18, 2.6),
    'dish_064': (375, 310, 15, 26, 3),
    'dish_110': (346, 250, 18, 19, 1.3),
    'dish_202': (343, 94, 6.3, 6.5, 2.7),
    'dish_266': (339, 240, 7.1, 15, 18),
    'dish_269': (355, 290, 20, 20, 6.9),
    'dish_339': (386, 140, 4, 5.1, 20),
    'dish_341': (471, 190, 6.9, 10, 16),
}
EXPECTED_PREPARATIONS = {
    'dish_004': ['as_served', 'braised'], 'dish_007': ['as_served', 'stir_fried'],
    'dish_012': ['as_served', 'stir_fried'], 'dish_064': ['as_served'],
    'dish_110': ['as_served', 'steamed'], 'dish_202': ['as_served', 'braised'],
    'dish_266': ['as_served'], 'dish_269': ['as_served', 'fried'],
    'dish_339': ['as_served', 'stir_fried'], 'dish_341': ['as_served'],
}


def fingerprint(value):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(text.encode()).hexdigest()


def test_only_ten_selected_references_change_existing_catalogue():
    assert SNAPSHOT['version'] == importer.VERSION == '2026-11-24.1'
    assert {food['id'] for food in SNAPSHOT['foods'] if 'measured_reference' in food} == (
        set(EXPECTED))
    ingredients = [food for food in SNAPSHOT['foods'] if food['kind'] == 'ingredient']
    assert len(ingredients) == 202
    assert len(RECIPES) == 384
    assert sum('measured_reference' not in recipe for recipe in RECIPES) == 374
    assert [food for food in SNAPSHOT['foods'] if food['kind'] == 'recipe'] == RECIPES
    assert fingerprint(ingredients) == (
        '4593b21c99d6cdb6df095a5c3ce0d90b87c0fe6ecb71d4b80c8168f164c3a661')
    assert all(food['source']['license'] == 'CC0-1.0' for food in ingredients)
    original_recipes = [{key: value for key, value in recipe.items()
                         if key != 'measured_reference'} for recipe in RECIPES]
    assert fingerprint(original_recipes) == (
        '623c8a0bbaa055b1f4cf72a997c352cdfa58f231d1b62a05b46c6872ce3a3f2b')
    assert fingerprint({recipe['id']: recipe['recipe'] for recipe in RECIPES}) == (
        '21fa5ec2902d4431e69d9b269d845786399b0ce792cf421196fe3c4ed13790a0')
    importer.validate_catalogue(SNAPSHOT['foods'])


@pytest.mark.parametrize('recipe_id', EXPECTED)
def test_published_vector_and_attribution_are_preserved(recipe_id):
    row, calories, protein, fat, carbs = EXPECTED[recipe_id]
    reference = BY_ID[recipe_id]['measured_reference']
    assert reference['nutrients'] == {
        'calories': calories, 'protein_g': protein, 'fat_g': fat, 'carbs_g': carbs}
    assert all(math.isfinite(value) and value > 0
               for value in reference['nutrients'].values())
    assert reference['nutrition_basis'] == 'per_100g_cooked_edible'
    assert reference['carbohydrate_basis'] == 'available'
    assert reference['match_scope'] == 'same_named_prepared_dish'
    assert reference['source']['id'] == f'CFS-FRL-Eng-{row}'
    assert reference['source']['url'] == importer.CFS_WORKBOOK_URL
    assert reference['source']['license'] == (
        'No open licence asserted; CFS copyright notice applies')
    evidence = next(record for record in MANIFEST['records']
                    if record['recipe_id'] == recipe_id)
    assert evidence['source_id'] == reference['source']['id']
    assert evidence['source_range'] == f'C{row}:I{row}'
    assert evidence['source_name_zh'] == reference['source_name_zh']
    assert evidence['source_name_en'] == reference['source_name_en']
    assert evidence['exact_recipe_composition_match'] is False
    assert evidence['source_values_per_100g'] == dict(
        reference['nutrients'], dietary_fibre=reference['dietary_fibre'])
    assert reference['notes_zh'] and reference['notes_en']
    assert reference['compatible_preparations'] == EXPECTED_PREPARATIONS[recipe_id]
    assert evidence['compatible_preparations'] == reference['compatible_preparations']
    for key in ('preparation_notes_zh', 'preparation_notes_en'):
        assert evidence[key] == reference[key]
        assert reference[key]


def test_preparation_is_derived_from_source_not_the_illustrative_recipe():
    steamed_chicken = BY_ID['dish_110']
    assert '煮熟' in steamed_chicken['method']  # Existing illustrative recipe is unchanged.
    assert steamed_chicken['measured_reference']['source_name_en'].startswith('Steamed')
    assert steamed_chicken['measured_reference']['compatible_preparations'] == [
        'as_served', 'steamed']
    for recipe_id in ('dish_064', 'dish_266', 'dish_341'):
        # These CFS descriptions do not specify a cooking route; do not infer one.
        assert BY_ID[recipe_id]['measured_reference']['compatible_preparations'] == [
            'as_served']


def test_source_energy_trace_fibre_and_observed_ranges_keep_their_meaning():
    refs = {key: BY_ID[key]['measured_reference'] for key in EXPECTED}
    assert refs['dish_266']['nutrients']['calories'] == 240
    assert 4 * 7.1 + 9 * 15 + 4 * 18 != 240  # Do not recalculate rounded source energy.
    for recipe_id in ('dish_004', 'dish_064', 'dish_110', 'dish_266', 'dish_269'):
        assert refs[recipe_id]['dietary_fibre'] == {'qualifier': 'trace'}
    assert refs['dish_012']['dietary_fibre'] == {'value_g': 0}
    assert refs['dish_341']['dietary_fibre'] == {'value_g': 1.1}
    assert refs['dish_012']['observed_ranges'] == {
        'calories': {'min': 180, 'max': 330}, 'fat_g': {'min': 13, 'max': 30}}
    assert refs['dish_266']['observed_ranges'] == {
        'calories': {'min': 190, 'max': 280}, 'fat_g': {'min': 11, 'max': 18}}
    for recipe_id, reference in refs.items():
        if recipe_id in {'dish_012', 'dish_266'}:
            assert reference['sample_count'] == 10
            assert reference['sample_collection_period'] == '2017-03/2017-04'
        else:
            assert not {'sample_count', 'sample_collection_period',
                        'observed_ranges', 'range_source_url'} & reference.keys()
    assert {record['recipe_id'] for record in MANIFEST['records']} == set(EXPECTED)
    assert MANIFEST['reference_count'] == 10
    assert MANIFEST['recipes_without_measured_reference'] == 374


@pytest.mark.parametrize('key,value', [
    ('carbohydrate_basis', 'total'), ('nutrition_basis', 'per_100g_raw'),
    ('id', 'cfs_frl_eng_339'), ('version', '2017'), ('source_name_en', ''),
    ('source_workbook_sha256', 'unverified'), ('retrieved_at', ''),
    ('compatible_preparations', []), ('compatible_preparations', 'as_served'),
    ('compatible_preparations', ['as_served', 'as_served']),
    ('compatible_preparations', ['as_served', 'raw']),
    ('compatible_preparations', ['as_served', 'other']),
    ('compatible_preparations', ['as_served', 'steamed']),
    ('compatible_preparations', ['stir_fried']),
    ('compatible_preparations', ['as_served', None]),
    ('compatible_preparations', ['as_served', {'stir_fried': True}]),
    ('preparation_notes_en', ''),
    ('nutrients', {'calories': 230, 'protein_g': 13, 'fat_g': 18}),
    ('nutrients', {'calories': 0, 'protein_g': 13, 'fat_g': 18, 'carbs_g': 2.6}),
    ('nutrients', {'calories': float('nan'), 'protein_g': 13, 'fat_g': 18, 'carbs_g': 2.6}),
    ('nutrients', {'calories': 230, 'protein_g': float('inf'), 'fat_g': 18, 'carbs_g': 2.6}),
    ('nutrients', {'calories': True, 'protein_g': 13, 'fat_g': 18, 'carbs_g': 2.6}),
    ('nutrients', {'calories': 230, 'protein_g': 13, 'fat_g': -1, 'carbs_g': 2.6}),
    ('dietary_fibre', {'qualifier': 'trace', 'value_g': 0}),
    ('dietary_fibre', {'value_g': float('nan')}), ('sample_count', 0),
    ('observed_ranges', {'calories': {'min': 331, 'max': 180},
                         'fat_g': {'min': 13, 'max': 30}}),
])
def test_import_rejects_malformed_reference(key, value):
    recipe = deepcopy(BY_ID['dish_012'])
    recipe['measured_reference'][key] = value
    with pytest.raises(ValueError, match='measured reference'):
        importer.validate_measured_reference(recipe)


@pytest.mark.parametrize('key,value', [
    ('id', ''), ('url', 'https://example.org/unverified'), ('name', ''),
    ('license', 'CC0-1.0'), ('rights_url', ''),
])
def test_import_rejects_missing_or_misrepresented_source(key, value):
    recipe = deepcopy(BY_ID['dish_012'])
    recipe['measured_reference']['source'][key] = value
    with pytest.raises(ValueError, match='measured reference'):
        importer.validate_measured_reference(recipe)


def test_reference_cannot_be_attached_to_an_unreviewed_dish_or_ingredient():
    for food_id in ('dish_001', 'shrimp'):
        food = deepcopy(BY_ID[food_id])
        food['measured_reference'] = deepcopy(BY_ID['dish_012']['measured_reference'])
        with pytest.raises(ValueError, match='measured reference'):
            importer.validate_measured_reference(food)


def test_offline_rebuild_retains_cfs_reference_and_failure_preserves_snapshot(
        tmp_path, monkeypatch):
    ingredient = BY_ID['shrimp']
    fid = ingredient['fdc_id']
    selection = [{'id': 'shrimp', 'name': 'Shrimp', 'fdc_id': fid,
                  'state': 'raw', 'aliases': ['Shrimp']}]
    (tmp_path / 'usda_selection.json').write_text(json.dumps(selection))
    recipe = deepcopy(BY_ID['dish_012'])
    recipe['recipe'] = {'ingredients': {'shrimp': 100}, 'yield_g': 100}
    (tmp_path / 'recipes.json').write_text(json.dumps([recipe]))
    archive_path = tmp_path / 'source.zip'
    nutrient_ids = {'1008': 'calories', '1003': 'protein_g',
                    '1004': 'fat_g', '1005': 'carbs_g'}
    nutrients = 'fdc_id,nutrient_id,amount\n' + ''.join(
        f'{fid},{key},{ingredient["nutrients"][name]}\n'
        for key, name in nutrient_ids.items())
    with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr('food.csv', f'fdc_id,description\n{fid},Test shrimp\n')
        archive.writestr('food_nutrient.csv', nutrients)
    monkeypatch.setattr(importer, 'DATA', tmp_path)
    importer.build(archive_path)
    previous = (tmp_path / 'catalogue.json').read_text()
    rebuilt = json.loads(previous)
    assert rebuilt['foods'][1] == recipe
    assert rebuilt['foods'][0]['source']['license'] == 'CC0-1.0'
    assert rebuilt['version'] == '2026-11-24.1'
    recipe['measured_reference']['nutrients']['fat_g'] = float('nan')
    (tmp_path / 'recipes.json').write_text(json.dumps([recipe]))
    with pytest.raises(ValueError, match='measured reference'):
        importer.build(archive_path)
    assert (tmp_path / 'catalogue.json').read_text() == previous
