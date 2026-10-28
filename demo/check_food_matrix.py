"""Opt-in live Qwen checks with varied synthetic foods and weights.

Run against the separate Qwen demo: python3 demo/check_food_matrix.py --live
This uses model quota, creates 17 synthetic records, and does not retry failures.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
KEYS = ("calories", "protein_g", "fat_g", "carbs_g")
CASES = [
    {"id": f"rice_{grams}g", "text": f"{grams}克白米饭，蒸熟后的可食重量，无额外油。",
     "mode": "basic", "items": {"rice": grams}}
    for grams in (50, 100, 200)
] + [
    {"id": "roast_chicken_100g", "text": "100克烤去皮鸡胸肉，熟可食重量，本份额外油0克。",
     "mode": "advanced", "items": {"chicken_roast": 100}},
    {"id": "boiled_egg_100g", "text": "100克水煮鸡蛋，去壳后的熟可食重量，没有额外油。",
     "mode": "advanced", "items": {"egg": 100}},
    {"id": "boiled_broccoli_150g", "text": "150克水煮西兰花，熟可食重量，没有额外油。",
     "mode": "advanced", "items": {"broccoli_cooked": 150}},
    {"id": "mixed_three_foods", "text": "白米饭100克，水煮鸡蛋去壳100克，水煮西兰花150克。"
     "全部是熟可食重量，没有额外油。", "mode": "advanced",
     "items": {"rice": 100, "egg": 100, "broccoli_cooked": 150}},
    {"id": "tomato_egg_200g", "text": "200克番茄炒蛋，熟可食重量。",
     "mode": "basic", "items": {"dish_001": 200}},
    {"id": "mapo_tofu_180g", "text": "180克麻婆豆腐，熟可食重量。",
     "mode": "basic", "items": {"dish_004": 180}},
    {"id": "kung_pao_250g", "text": "250克宫保鸡丁，熟可食重量。",
     "mode": "basic", "items": {"dish_003": 250}},
    {"id": "dumplings_10_pieces", "text": "十个白菜猪肉饺子，煮熟后吃的，不知道克数。",
     "mode": "basic", "items": {"dish_241": 200}, "assumed": True},
    {"id": "missing_weight_basic", "text": "白米饭，蒸熟后吃的，不知道重量。",
     "mode": "basic", "items": {"rice": 150}, "assumed": True},
    {"id": "missing_weight_advanced", "text": "白米饭，蒸熟后吃的，不知道重量。",
     "mode": "advanced", "expect": "clarify_grams"},
    {"id": "zero_grams", "text": "0克白米饭，熟重。这个0克不是缺少重量，不要替我改成一份。",
     "mode": "basic", "expect": "reject_or_clarify"},
    {"id": "negative_grams", "text": "负100克白米饭（-100克），熟重，请检查这个重量。",
     "mode": "advanced", "expect": "reject_or_clarify"},
    {"id": "over_limit_grams", "text": "10001克白米饭，熟重。",
     "mode": "basic", "expect": "reject_or_clarify"},
    {"id": "unsupported_food", "text": "100克虚构的星际能量胶，配方和成分都未知。"
     "不要把它替换为其他食品。", "mode": "advanced", "expect": "clarify_food"},
]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def request(base_url, method, path, payload=None):
    req = urllib.request.Request(
        base_url.rstrip("/") + path, method=method,
        data=json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        response = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return {"status": response.status, "body": json.load(response)}


def ready(base_url, meal):
    deadline = time.monotonic() + 150
    while meal["status"] == "queued" and time.monotonic() < deadline:
        time.sleep(0.5)
        result = request(base_url, "GET", "/analyses/" + meal["id"])
        require(result["status"] == 200, "Polling did not return HTTP 200")
        meal = result["body"]
    require(meal["status"] != "queued", "Worker did not finish within 150 seconds")
    return meal


def finite_nonnegative(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value) and value >= 0


def catalogue_totals(foods, expected_items):
    totals = dict.fromkeys(KEYS, 0.0)
    for food_id, grams in expected_items.items():
        food = foods[food_id]
        if food["kind"] == "recipe":
            recipe = food["recipe"]
            for key in KEYS:
                per_batch = sum(foods[ingredient]["nutrients"][key] * amount / 100
                                for ingredient, amount in recipe["ingredients"].items())
                totals[key] += per_batch * grams / recipe["yield_g"]
        else:
            for key in KEYS:
                totals[key] += food["nutrients"][key] * grams / 100
    return {key: round(value, 1) for key, value in totals.items()}


def validate(case, meal, foods):
    expected = case.get("expect", "completed")
    if expected != "completed":
        require(all(meal.get(key) is None for key in KEYS),
                "Ambiguous/invalid input returned nutrition totals")
        if expected == "reject_or_clarify" and meal["status"] == "failed":
            require(bool(meal.get("error_message")), "Rejection has no user-facing error")
            raise AssertionError(
                "No nutrition totals were shown, but a generic failed state cannot prove "
                "input-specific validation or successful clarification"
            )
        require(meal["status"] == "needs_input" and meal.get("questions"),
                "Expected clarification instead of a model/service failure")
        if expected in ("clarify_grams", "reject_or_clarify"):
            require(any(q["key"].endswith(".grams") for q in meal["questions"]),
                    "The app did not ask for the missing or invalid gram weight")
        elif expected == "clarify_food":
            require(any(q["kind"] == "food" for q in meal["questions"]),
                    "Unsupported food was not left for user matching")
        return "Missing facts require user clarification; no nutrition totals shown."

    require(meal["status"] == "completed", f"Expected completed, received {meal['status']}")
    require(not meal.get("questions"), "Completed meal still has pending questions")
    details = meal.get("details", [])
    require(len(details) == len(case["items"]), "Food was omitted or duplicated")
    actual = {detail["food_id"]: detail["grams"] for detail in details}
    require(actual == case["items"], f"Food IDs or gram amounts differ: {actual}")
    draft = {item["food_id"]: item for item in meal["draft"]}
    for food_id, grams in case["items"].items():
        if case.get("assumed"):
            require(draft[food_id].get("grams") is None,
                    "A default portion was incorrectly saved as user-provided grams")
        else:
            require(draft[food_id].get("grams") == grams, "Explicit grams were not preserved")
    if case.get("assumed"):
        require(all(any("未提供克数" in note for note in item["assumptions"])
                    for item in details), "Default portion was not labelled as an assumption")
    expected_totals = catalogue_totals(foods, case["items"])
    for key in KEYS:
        require(finite_nonnegative(meal.get(key)), f"Invalid meal total: {key}")
        require(all(finite_nonnegative(item["nutrients"].get(key)) for item in details),
                f"Invalid per-food value: {key}")
        detail_sum = sum(item["nutrients"][key] for item in details)
        require(abs(meal[key] - detail_sum) <= 0.051 * (len(details) + 1),
                f"Meal {key} disagrees with rounded detail sum")
        require(abs(meal[key] - expected_totals[key]) <= 0.100001,
                f"Meal {key} disagrees with catalogue arithmetic: "
                f"got {meal[key]}, expected {expected_totals[key]}")
    return "Correct food/grams, finite nonnegative totals, detail sums and catalogue arithmetic."


def validate_proportionality(results):
    meals = {row["id"]: row["meal"] for row in results if row.get("passed")}
    require(all(f"rice_{grams}g" in meals for grams in (50, 100, 200)),
            "Cannot verify proportionality because a rice case failed")
    for grams in (50, 200):
        for key in KEYS:
            expected = meals["rice_100g"][key] * grams / 100
            require(abs(meals[f"rice_{grams}g"][key] - expected) <= 0.100001,
                    f"Rice {grams}g {key} is not proportional to the 100g result")


def check(base_url, output):
    report = {"observed_at": datetime.now(timezone.utc).isoformat(),
              "scope": "17 synthetic live Qwen inputs; no automatic retries; no confirmation.",
              "base_url": base_url, "passed": False, "cases": []}

    def save():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    try:
        catalogue = request(base_url, "GET", "/foods")
        require(catalogue["status"] == 200, "Cannot read the target's supported foods")
        require(catalogue["body"].get("provider") == "qwen", "The target must use real Qwen")
        paths = request(base_url, "GET", "/openapi.json")["body"].get("paths", {})
        require(not any(path.startswith(("/auth/", "/profile", "/tracking")) for path in paths),
                "This script checks the nutrichat branch, not test accounts/personalization")
        foods = {food["id"]: food for food in catalogue["body"]["catalogue"]["foods"]}
        for case in CASES:
            row = {"id": case["id"], "input": case["text"], "mode": case["mode"],
                   "passed": False}
            try:
                created = request(base_url, "POST", "/analyses", {
                    "food_text": case["text"], "mode": case["mode"],
                })
                row["create_status"] = created["status"]
                require(created["status"] == 201, "Meal was not accepted as a queued analysis")
                row["job_id"] = created["body"]["job"]["id"]
                row["meal"] = ready(base_url, created["body"]["analysis"])
                row["observation"] = validate(case, row["meal"], foods)
                row["passed"] = True
            except (AssertionError, ValueError, KeyError, TypeError, OSError) as error:
                row["failure"] = str(error)
            report["cases"].append(row)
            save()
            print(f"{'PASS' if row['passed'] else 'FAIL'} {row['id']}: "
                  f"{row.get('observation', row.get('failure'))}", flush=True)
        try:
            validate_proportionality(report["cases"])
            report["rice_proportionality"] = {"passed": True}
        except AssertionError as error:
            report["rice_proportionality"] = {"passed": False, "failure": str(error)}
        report["passed"] = (all(row["passed"] for row in report["cases"])
                            and report["rice_proportionality"]["passed"])
    except (AssertionError, ValueError, KeyError, OSError) as error:
        report["preflight_failure"] = str(error)
    except KeyboardInterrupt:
        report["interrupted"] = True
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        save()
    passed = sum(row["passed"] for row in report["cases"])
    print(f"{passed}/{len(report['cases'])} food cases passed. Evidence: {output}", flush=True)
    return report["passed"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8003")
    parser.add_argument("--output", type=Path, default=ROOT / "demo/output/food-matrix.json")
    parser.add_argument("--live", action="store_true", help="Use model quota and create records")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required to use model quota and create synthetic records")
    return 0 if check(args.base_url, args.output) else 1


if __name__ == "__main__":
    sys.exit(main())
