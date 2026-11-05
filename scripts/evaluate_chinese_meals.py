"""Validate a fixed Chinese corpus and optionally evaluate it through the live API.

The corpus tests extraction and catalogue arithmetic. It cannot measure the actual
calories of a prepared meal without independently measured ingredients and portions.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

from services.common.http_auth import CheckAuthenticationError, authenticated_client
from services.common.meal_engine import catalogue

CORPUS = Path(__file__).resolve().parents[1] / "evaluation" / "chinese_meals.json"
MISSING = object()


def validate_corpus(data: dict) -> list[dict]:
    if data.get("version") != 1 or not isinstance(data.get("cases"), list):
        raise ValueError("Corpus must contain version 1 and a cases list")
    known_ids = {food["id"] for food in catalogue()["foods"]}
    seen = set()
    for case in data["cases"]:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError("Case IDs must be unique non-empty strings")
        seen.add(case_id)
        if (case.get("mode") not in {"basic", "advanced"}
                or case.get("expected_status") not in {"completed", "needs_input"}
                or not isinstance(case.get("category"), str) or not case["category"]
                or not isinstance(case.get("text"), str) or not case["text"].strip()
                or not isinstance(case.get("expected_items"), list)
                or not case["expected_items"]):
            raise ValueError(f"Invalid case definition: {case_id}")
        for item in case["expected_items"]:
            if not isinstance(item, dict):
                raise ValueError(f"Invalid expected item in {case_id}")
            if item.get("food_id", MISSING) is MISSING or item["food_id"] not in {
                *known_ids, None,
            }:
                raise ValueError(f"Unknown expected food ID in {case_id}")
            if "draft_grams" in item and item["draft_grams"] is not None:
                if not isinstance(item["draft_grams"], (int, float)) or item["draft_grams"] <= 0:
                    raise ValueError(f"Invalid expected weight in {case_id}")
        if "catalogue_calories" in case:
            if case["expected_status"] != "completed" or case["catalogue_calories"] < 0:
                raise ValueError(f"Invalid calorie reference in {case_id}")
    if not seen:
        raise ValueError("Corpus must contain at least one case")
    return data["cases"]


def assess(case: dict, analysis: dict) -> tuple[str, list[str]]:
    """Return one outcome and readable, independently checkable mismatches."""
    status = analysis.get("status")
    if status == "queued":
        return "timeout", ["The analysis did not finish before the deadline"]
    if status == "failed":
        return "processing_failure", [analysis.get("error_message") or "Analysis failed"]
    if status not in {"completed", "needs_input"}:
        return "invalid_response", [f"Unexpected analysis status: {status}"]

    issues = []
    if status != case["expected_status"]:
        issues.append(f"Expected status {case['expected_status']}; observed {status}")
    draft = analysis.get("draft")
    if not isinstance(draft, list):
        return "invalid_response", ["Analysis draft is missing"]
    expected = case["expected_items"]
    if len(draft) != len(expected):
        issues.append(f"Expected {len(expected)} food items; observed {len(draft)}")
    for index, item in enumerate(expected):
        if index >= len(draft):
            break
        actual = draft[index]
        if not isinstance(actual, dict):
            return "invalid_response", [f"Draft item {index} is invalid"]
        for field, expected_value in item.items():
            actual_field = "grams" if field == "draft_grams" else field
            observed = actual.get(actual_field, MISSING)
            if observed is MISSING or observed != expected_value:
                issues.append(
                    f"Item {index} {actual_field}: expected {expected_value!r}; "
                    f"observed {None if observed is MISSING else observed!r}"
                )
    if status == "needs_input" and any(analysis.get(key) is not None for key in (
        "calories", "protein_g", "fat_g", "carbs_g",
    )):
        issues.append("Pending clarification has non-null nutrient totals")
    if status == "needs_input" and not analysis.get("questions"):
        issues.append("Pending clarification has no questions")
    reference = case.get("catalogue_calories")
    if reference is not None and status == "completed":
        observed = analysis.get("calories")
        if not isinstance(observed, (int, float)) or abs(observed - reference) > 0.1:
            issues.append(f"Catalogue calories: expected {reference}; observed {observed}")
    return ("pass" if not issues else "mismatch"), issues


def run_case(client: httpx.Client, case: dict, deadline_seconds: float) -> dict:
    started = time.monotonic()
    result = {"id": case["id"], "category": case["category"], "outcome": None,
              "issues": [], "analysis_id": None, "status": None, "calories": None,
              "catalogue_reference_calories": case.get("catalogue_calories"),
              "catalogue_absolute_error_kcal": None, "observed_items": []}
    try:
        response = client.post("/analyses", json={"food_text": case["text"], "mode": case["mode"]})
        response.raise_for_status()
        analysis = response.json()["analysis"]
        result["analysis_id"] = analysis["id"]
        while analysis.get("status") == "queued" and time.monotonic()-started < deadline_seconds:
            time.sleep(1)
            response = client.get("/analyses/" + analysis["id"])
            response.raise_for_status()
            analysis = response.json()
        result["status"] = analysis.get("status")
        result["calories"] = analysis.get("calories")
        result["observed_items"] = [
            {key: item.get(key) for key in (
                "food_id", "grams", "portion_count", "portion_unit",
                "weight_includes_inedible",
            )}
            for item in analysis.get("draft", []) if isinstance(item, dict)
        ]
        if (case.get("catalogue_calories") is not None
                and isinstance(analysis.get("calories"), (int, float))):
            result["catalogue_absolute_error_kcal"] = round(
                abs(analysis["calories"] - case["catalogue_calories"]), 1
            )
        result["outcome"], result["issues"] = assess(case, analysis)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        result["outcome"] = "transport_or_response_failure"
        result["issues"] = [f"{type(exc).__name__}: request or response failed"]
    result["elapsed_seconds"] = round(time.monotonic()-started, 2)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--live", action="store_true", help="Call Qwen through a running stack")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--deadline-seconds", type=float, default=90)
    parser.add_argument("--output", type=Path, help="Write a JSON report; required with --live")
    args = parser.parse_args()
    try:
        cases = validate_corpus(json.loads(args.corpus.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    if not args.live:
        print(f"Corpus valid: {len(cases)} cases across "
              f"{len({case['category'] for case in cases})} categories. No provider called.")
        return 0
    if args.output is None or args.deadline_seconds <= 0:
        parser.error("--live requires --output and a positive --deadline-seconds")
    try:
        with authenticated_client(args.base_url, timeout=25) as client:
            provider = client.get("/foods")
            provider.raise_for_status()
            if provider.json().get("provider") != "qwen":
                parser.error("The target stack is not using Qwen; refusing a demo-mode evaluation")
            results = [run_case(client, case, args.deadline_seconds) for case in cases]
    except (CheckAuthenticationError, httpx.HTTPError) as exc:
        print(f"Evaluation could not start: {exc}", file=sys.stderr)
        return 2
    counts = Counter(result["outcome"] for result in results)
    report = {
        "corpus_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "qwen",
        "note": "Catalogue checks are not measured real-meal calorie accuracy.",
        "summary": dict(counts),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Report: {args.output}")
    print("Outcomes: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    return 0 if counts.get("pass") == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
