"""Approximate daily energy balance from recorded intake and exercise.

The sedentary factor supplies a simple non-exercise baseline. Using the profile's
activity-adjusted maintenance estimate here would count logged exercise twice.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def _one_decimal(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def calculate_energy_balance(
    *, intake_kcal: float | None, exercise_kcal: float | None,
    resting_kcal: float | None,
) -> dict:
    """Return one nonnegative balance value, or nulls when inputs are incomplete."""
    if resting_kcal is None:
        return {
            "baseline_expenditure_kcal": None,
            "total_expenditure_kcal": None,
            "balance_type": None,
            "balance_kcal": None,
        }
    baseline = _one_decimal(Decimal(str(resting_kcal)) * Decimal("1.2"))
    if exercise_kcal is None:
        return {
            "baseline_expenditure_kcal": baseline,
            "total_expenditure_kcal": None,
            "balance_type": None,
            "balance_kcal": None,
        }
    expenditure = _one_decimal(Decimal(str(baseline)) + Decimal(str(exercise_kcal)))
    if intake_kcal is None:
        return {
            "baseline_expenditure_kcal": baseline,
            "total_expenditure_kcal": expenditure,
            "balance_type": None,
            "balance_kcal": None,
        }
    difference = _one_decimal(Decimal(str(intake_kcal)) - Decimal(str(expenditure)))
    balance_type = "surplus" if difference > 0 else "deficit" if difference < 0 else "balanced"
    return {
        "baseline_expenditure_kcal": baseline,
        "total_expenditure_kcal": expenditure,
        "balance_type": balance_type,
        "balance_kcal": abs(difference),
    }
