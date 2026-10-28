"""Ensure the live probe cannot report incorrect or invented nutrition as a pass."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def matrix():
    source = Path(__file__).resolve().parents[2] / "demo" / "check_food_matrix.py"
    spec = importlib.util.spec_from_file_location("demo_food_matrix", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def complete_meal():
    nutrients = {"calories": 130, "protein_g": 2.7, "fat_g": 0.3, "carbs_g": 28}
    return {
        "status": "completed", "questions": [], **nutrients,
        "draft": [{"food_id": "rice", "grams": 100}],
        "details": [{"food_id": "rice", "grams": 100, "nutrients": nutrients,
                     "assumptions": ["按用户提供的100克计算"]}],
    }


@pytest.fixture
def foods():
    return {"rice": {"kind": "ingredient", "nutrients": {
        "calories": 130, "protein_g": 2.7, "fat_g": 0.3, "carbs_g": 28,
    }}}


def test_matrix_is_bounded_and_varied(matrix):
    assert len(matrix.CASES) == 17
    assert len({case["id"] for case in matrix.CASES}) == 17
    assert {"basic", "advanced"} == {case["mode"] for case in matrix.CASES}
    assert {"rice_50g", "rice_100g", "rice_200g", "mixed_three_foods", "zero_grams",
            "negative_grams", "over_limit_grams", "unsupported_food"} <= {
                case["id"] for case in matrix.CASES}


def test_completed_meal_must_match_food_grams_and_arithmetic(matrix, complete_meal, foods):
    case = {"items": {"rice": 100}}
    matrix.validate(case, complete_meal, foods)
    complete_meal["details"][0]["grams"] = 200
    with pytest.raises(AssertionError, match="gram amounts differ"):
        matrix.validate(case, complete_meal, foods)


def test_matching_detail_sums_cannot_hide_wrong_catalogue_math(matrix, complete_meal, foods):
    complete_meal["calories"] = complete_meal["details"][0]["nutrients"]["calories"] = 999
    with pytest.raises(AssertionError, match="catalogue arithmetic"):
        matrix.validate({"items": {"rice": 100}}, complete_meal, foods)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, None, True, "130"])
def test_invalid_nutrients_never_pass(matrix, complete_meal, foods, value):
    complete_meal["calories"] = value
    with pytest.raises(AssertionError, match="Invalid meal total"):
        matrix.validate({"items": {"rice": 100}}, complete_meal, foods)


def test_invalid_weight_cannot_succeed_with_default_portion(matrix, complete_meal):
    with pytest.raises(AssertionError, match="returned nutrition totals"):
        matrix.validate({"expect": "reject_or_clarify"}, complete_meal, {})


def test_generic_failed_state_is_not_claimed_as_input_validation(matrix):
    meal = {"status": "failed", "error_message": "Please review your input."}
    with pytest.raises(AssertionError, match="cannot prove input-specific validation"):
        matrix.validate({"expect": "reject_or_clarify"}, meal, {})


def test_service_failure_is_not_a_successful_clarification(matrix):
    with pytest.raises(AssertionError, match="model/service failure"):
        matrix.validate({"expect": "clarify_grams"}, {
            "status": "failed", "error_message": "Provider unavailable",
        }, {})


def test_advanced_missing_weight_requires_gram_question(matrix):
    meal = {"status": "needs_input", "questions": [{"key": "0.preparation"}]}
    with pytest.raises(AssertionError, match="missing or invalid gram weight"):
        matrix.validate({"expect": "clarify_grams"}, meal, {})
    meal["questions"] = [{"key": "0.grams"}]
    matrix.validate({"expect": "clarify_grams"}, meal, {})


def test_assumed_weight_must_not_be_saved_as_explicit(matrix, complete_meal, foods):
    with pytest.raises(AssertionError, match="saved as user-provided"):
        matrix.validate({"items": {"rice": 100}, "assumed": True}, complete_meal, foods)
    complete_meal["draft"][0]["grams"] = None
    with pytest.raises(AssertionError, match="not labelled"):
        matrix.validate({"items": {"rice": 100}, "assumed": True}, complete_meal, foods)


def test_proportionality_requires_all_successful_samples(matrix, complete_meal):
    rows = [{"id": "rice_100g", "meal": complete_meal, "passed": True}]
    with pytest.raises(AssertionError, match="rice case failed"):
        matrix.validate_proportionality(rows)
