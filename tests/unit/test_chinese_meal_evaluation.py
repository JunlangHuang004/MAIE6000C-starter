import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.evaluate_chinese_meals import CORPUS, assess, validate_corpus


def test_corpus_is_valid_and_covers_distinct_failure_modes():
    cases = validate_corpus(json.loads(Path(CORPUS).read_text(encoding="utf-8")))
    assert len(cases) >= 7
    assert {case["category"] for case in cases} >= {
        "explicit_weight", "count_vs_grams", "reference_recipe",
        "inedible_weight", "unsupported_food",
    }


def test_assessment_separates_catalogue_match_from_quantity_errors():
    case = {
        "expected_status": "completed",
        "expected_items": [{"food_id": "egg", "draft_grams": 100}],
        "catalogue_calories": 155,
    }
    analysis = {"status": "completed", "draft": [{"food_id": "egg", "grams": 100}],
                "calories": 155}
    assert assess(case, analysis) == ("pass", [])
    wrong_grams = deepcopy(analysis)
    wrong_grams["draft"][0]["grams"] = 2
    outcome, issues = assess(case, wrong_grams)
    assert outcome == "mismatch" and "grams" in issues[0]
    wrong_calories = deepcopy(analysis)
    wrong_calories["calories"] = 200
    outcome, issues = assess(case, wrong_calories)
    assert outcome == "mismatch" and "Catalogue calories" in issues[0]


def test_pending_question_requires_null_totals_and_an_actual_question():
    case = {"expected_status": "needs_input", "expected_items": [{"food_id": None}]}
    analysis = {"status": "needs_input", "draft": [{"food_id": None}],
                "questions": [{"key": "0.food_id"}], "calories": None}
    assert assess(case, analysis) == ("pass", [])
    analysis["calories"] = 100
    analysis["questions"] = []
    outcome, issues = assess(case, analysis)
    assert outcome == "mismatch" and len(issues) == 2


@pytest.mark.parametrize("status,expected", [
    ("queued", "timeout"), ("failed", "processing_failure"),
    ("unknown", "invalid_response"),
])
def test_non_result_statuses_are_reported_separately(status, expected):
    outcome, _ = assess({"expected_status": "completed"}, {"status": status})
    assert outcome == expected
