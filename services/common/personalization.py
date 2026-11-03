"""Deterministic adult energy references, independent of Qwen and meal processing.

The resting equation is Mifflin et al. (1990), PMID 2305711. Activity factors,
goal adjustments, macro split and automatic-output limits are explicit product
assumptions, not a clinical prescription. See docs/personalization.md.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol


FORMULA_VERSION = "mifflin-1990-nutrichat-v1"
ACTIVITY_FACTORS = {
    "sedentary": Decimal("1.2"),
    "light": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "high": Decimal("1.725"),
}
GOAL_ADJUSTMENTS = {"gain_muscle": Decimal("0.05"), "lose_fat": Decimal("-0.10")}
MACRO_ENERGY_SHARES = {
    "protein_g": (Decimal("0.25"), Decimal("4")),
    "fat_g": (Decimal("0.30"), Decimal("9")),
    "carbs_g": (Decimal("0.45"), Decimal("4")),
}
# Below these limits we withhold targets, rather than silently raising the result.
# These are conservative application boundaries, not universal intake requirements.
AUTOMATIC_ENERGY_MINIMUM = {"male": Decimal("1500"), "female": Decimal("1200")}


class ProfileValues(Protocol):
    age_years: int
    height_cm: float
    weight_kg: float
    sex: str
    goal: str
    activity_level: str


def _one_decimal(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def calculate_reference(profile: ProfileValues) -> dict:
    """Calculate from validated profile values without writing or sending any data.

    Guard comparisons use unrounded values. All macro grams derive from the displayed
    calorie reference; display rounding is not represented as measurement accuracy.
    """
    weight = Decimal(str(profile.weight_kg))
    height = Decimal(str(profile.height_cm))
    age = Decimal(profile.age_years)
    resting = 10 * weight + Decimal("6.25") * height - 5 * age
    resting += Decimal("5") if profile.sex == "male" else Decimal("-161")
    activity_factor = ACTIVITY_FACTORS[profile.activity_level]
    adjustment = GOAL_ADJUSTMENTS[profile.goal]
    maintenance = resting * activity_factor
    proposed = maintenance * (1 + adjustment)
    bmi = weight / (height / 100) ** 2

    reasons = []
    if profile.goal == "lose_fat" and bmi < Decimal("18.5"):
        reasons.append("underweight_fat_loss")
    if proposed < AUTOMATIC_ENERGY_MINIMUM[profile.sex]:
        reasons.append("low_energy_reference")
    if proposed < resting:
        reasons.append("below_resting_reference")

    notes = [
        "这是根据所填资料推算的每日参考，并非测量值或必须达到的指标。",
        "活动系数、增肌加 5%／减脂减 10% 和营养比例是本项目的简化假设。",
        "营养参考按热量的 25% 蛋白质、30% 脂肪、45% 碳水化合物换算。",
        "增肌也取决于力量训练、休息等因素；此参考不预测体重或肌肉变化。",
        "适用于 18–80 岁一般健康成人；孕哺期或需要临床饮食管理时应使用专业指导。",
    ]
    if reasons:
        notes.append("当前资料超出本工具自动生成目标的范围，已保留资料但不显示热量与营养目标。")

    result = {
        "status": "needs_review" if reasons else "estimated",
        "formula_version": FORMULA_VERSION,
        "resting_kcal": _one_decimal(resting),
        "maintenance_kcal": _one_decimal(maintenance),
        "activity_factor": float(activity_factor),
        "goal_adjustment": float(adjustment),
        "bmi": _one_decimal(bmi),
        "calories": None,
        "protein_g": None,
        "carbs_g": None,
        "fat_g": None,
        "reason_codes": reasons,
        "notes": notes,
    }
    if not reasons:
        calories = proposed.quantize(Decimal("1E1"), rounding=ROUND_HALF_UP)
        result["calories"] = int(calories)
        for name, (share, kcal_per_gram) in MACRO_ENERGY_SHARES.items():
            result[name] = _one_decimal(calories * share / kcal_per_gram)
    return result
