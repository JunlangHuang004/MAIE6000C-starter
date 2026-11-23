"""Deterministic adult energy references, independent of Qwen and meal processing.

The resting equation is Mifflin et al. (1990), PMID 2305711. Activity factors,
goal adjustments, macro split and automatic-output limits are explicit product
assumptions, not a clinical prescription. See docs/personalization.md.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol


FORMULA_VERSION = "mifflin-evidence-2026-v2"
ACTIVITY_FACTORS = {
    "sedentary": Decimal("1.2"),
    "light": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "high": Decimal("1.725"),
}
# These are starting policies informed by the sources below. No guideline mandates
# a 15% deficit or establishes 500 kcal as a universal safety threshold.
GOAL_ADJUSTMENTS = {"gain_muscle": Decimal("0.05"), "lose_fat": Decimal("-0.15")}
MAXIMUM_ENERGY_DEFICIT = Decimal("500")
PROTEIN_REFERENCES = {
    "gain_muscle": (Decimal("1.6"), Decimal("1.6"), Decimal("2.2")),
    "trained_loss": (Decimal("1.8"), Decimal("1.6"), Decimal("2.2")),
    "untrained_loss": (Decimal("1.4"), Decimal("1.2"), Decimal("1.6")),
}
# Below these limits we withhold targets, rather than silently raising the result.
# These are conservative application boundaries, not universal intake requirements.
AUTOMATIC_ENERGY_MINIMUM = {"male": Decimal("1500"), "female": Decimal("1200")}
SOURCES = (
    {
        "title": "Mifflin et al. (1990): resting energy expenditure equation",
        "url": "https://pubmed.ncbi.nlm.nih.gov/2305711/",
    },
    {
        "title": "Helms et al. (2023): small and large surpluses during resistance training",
        "url": "https://link.springer.com/article/10.1186/s40798-023-00651-y",
    },
    {
        "title": "Morton et al. (2018): protein and resistance training meta-analysis",
        "url": "https://pubmed.ncbi.nlm.nih.gov/28698222/",
    },
    {
        "title": "ISSN (2026): diets for body weight reduction position stand",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13665703/",
    },
    {
        "title": "Health Canada: macronutrient dietary reference intakes and AMDR",
        "url": "https://www.canada.ca/en/health-canada/services/food-nutrition/"
               "healthy-eating/dietary-reference-intakes/tables/reference-values-macronutrients.html",
    },
    {
        "title": "Garthe et al. (2011): slower and faster weight loss in athletes",
        "url": "https://pubmed.ncbi.nlm.nih.gov/21558571/",
    },
    {
        "title": "Murphy and Koehler (2022): energy deficit and resistance training meta-analysis",
        "url": "https://pubmed.ncbi.nlm.nih.gov/34623696/",
    },
    {
        "title": "NICE NG246: supported dietary approaches and low-energy diets",
        "url": "https://www.nice.org.uk/guidance/ng246/chapter/Physical-activity-and-diet",
    },
)


class ProfileValues(Protocol):
    age_years: int
    height_cm: float
    weight_kg: float
    sex: str
    goal: str
    activity_level: str
    strength_training: bool | None
    reference_scope: str | None


def _one_decimal(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def calculate_reference(profile: ProfileValues) -> dict:
    """Calculate from validated profile values without writing or sending any data.

    Eligibility and energy guards use unrounded values. Protein derives from actual
    body weight; fat and residual carbohydrate use the displayed calorie reference.
    Macro guards use unrounded grams/shares, before independent display rounding.
    """
    weight = Decimal(str(profile.weight_kg))
    height = Decimal(str(profile.height_cm))
    age = Decimal(profile.age_years)
    resting = 10 * weight + Decimal("6.25") * height - 5 * age
    resting += Decimal("5") if profile.sex == "male" else Decimal("-161")
    activity_factor = ACTIVITY_FACTORS[profile.activity_level]
    maintenance = resting * activity_factor
    energy_adjustment = maintenance * GOAL_ADJUSTMENTS[profile.goal]
    if profile.goal == "lose_fat":
        energy_adjustment = max(energy_adjustment, -MAXIMUM_ENERGY_DEFICIT)
    proposed = maintenance + energy_adjustment
    adjustment = energy_adjustment / maintenance
    bmi = weight / (height / 100) ** 2
    # Existing rows and old callers must explicitly confirm the new applicability
    # fields; missing attributes are equivalent to the migration's nullable values.
    scope = getattr(profile, "reference_scope", None)
    training = getattr(profile, "strength_training", None)

    reasons = []
    if scope is None:
        reasons.append("scope_confirmation_required")
    elif scope == "professional_guidance":
        reasons.append("professional_guidance_required")
    if training is None:
        reasons.append("training_confirmation_required")
    elif profile.goal == "gain_muscle" and training is False:
        reasons.append("strength_training_required")
    if bmi < Decimal("18.5"):
        reasons.append("underweight_reference")
    # A product scope boundary, not a diagnosis or an invalidation of Mifflin's
    # equation. Do not invent an adjusted body weight for protein at high BMI.
    if bmi >= Decimal("40"):
        reasons.append("high_bmi_reference")
    if proposed < AUTOMATIC_ENERGY_MINIMUM[profile.sex]:
        reasons.append("low_energy_reference")
    if proposed < resting:
        reasons.append("below_resting_reference")

    notes = [
        "这是根据所填资料推算的每日参考，并非测量值或必须达到的指标。",
        "静息热量采用 Mifflin–St Jeor 公式，活动系数只是对日常消耗的粗略估计。",
        "增肌默认加 5%；减脂默认减 15% 且每天最多减 500 千卡。这是本工具的起始策略，"
        "并非指南规定的唯一方案，也不是对每个人都适用的安全阈值。",
        "蛋白质按当前实际体重换算；增肌默认 1.6 克/千克，有力量训练的减脂默认 1.8 克/千克，"
        "两者参考范围均为 1.6–2.2 克/千克；无力量训练的减脂默认 1.4 克/千克，"
        "参考范围为 1.2–1.6 克/千克。默认值不是已证实的个人最优值，"
        "文献范围内的每个值也不一定都适合当前热量。",
        "脂肪先按热量的 30% 分配，必要时在参考范围内降低，为碳水化合物保留至少 45%。"
        "18 岁的脂肪至少占 25%、蛋白质最多占 30%；19 岁及以上分别为 20% 和 35%。"
        "30% 是分配选择；无法兼顾蛋白质、脂肪与碳水参考范围时不生成目标。",
        "增肌参考以力量训练为前提；训练、休息和个体差异都会影响结果，不保证体重或肌肉变化。",
        "适用于已确认适用范围的 18–80 岁一般健康成人；孕哺期、进食障碍、"
        "影响营养需求的疾病或已有专业饮食安排时，应使用专业指导。",
        "BMI 低于 18.5 或达到 40 是本工具停止自动生成目标的范围边界，"
        "不是诊断，也不表示 Mifflin 公式在较高 BMI 时失效。",
        "建议 2–4 周后结合体重趋势、训练表现、饥饿感和恢复情况复核；"
        "本工具不会依据这些趋势自动调整目标。",
    ]

    result = {
        "formula_version": FORMULA_VERSION,
        "resting_kcal": _one_decimal(resting),
        "maintenance_kcal": _one_decimal(maintenance),
        "activity_factor": float(activity_factor),
        "goal_adjustment": float(adjustment),
        "energy_adjustment_kcal": _one_decimal(energy_adjustment),
        "bmi": _one_decimal(bmi),
        "calories": None,
        "protein_g": None,
        "carbs_g": None,
        "fat_g": None,
        "protein_g_per_kg": None,
        "protein_reference_min_g_per_kg": None,
        "protein_reference_max_g_per_kg": None,
        "protein_min_g": None,
        "protein_max_g": None,
        "protein_energy_percent": None,
        "fat_energy_percent": None,
        "carbs_energy_percent": None,
        "reason_codes": reasons,
        "notes": notes,
        "sources": [dict(source) for source in SOURCES],
    }
    if not reasons:
        calories = proposed.quantize(Decimal("1E1"), rounding=ROUND_HALF_UP)
        protein_kind = "gain_muscle" if profile.goal == "gain_muscle" else (
            "trained_loss" if training else "untrained_loss"
        )
        protein_rate, protein_min, protein_max = PROTEIN_REFERENCES[protein_kind]
        protein = weight * protein_rate
        protein_energy = protein * 4
        # Equivalent to min(.30, .55 - protein_share), in energy units so
        # recurring Decimal division cannot spuriously fail an exact boundary.
        fat_energy = min(calories * Decimal("0.30"), calories * Decimal("0.55") -
                         protein_energy)
        fat = fat_energy / 9
        carbs_energy = calories - protein_energy - fat_energy
        carbs = carbs_energy / 4
        minimum_fat_share = Decimal("0.25") if profile.age_years == 18 else Decimal("0.20")
        maximum_protein_share = Decimal("0.30") if profile.age_years == 18 else Decimal("0.35")
        if (not calories * Decimal("0.10") <= protein_energy <= calories * maximum_protein_share
                or not calories * minimum_fat_share <= fat_energy <= calories * Decimal("0.30")
                or not calories * Decimal("0.45") <= carbs_energy <= calories * Decimal("0.65")
                or carbs < 130):
            reasons.append("macro_distribution_out_of_scope")
        else:
            result.update({
                "calories": int(calories),
                "protein_g": _one_decimal(protein),
                "fat_g": _one_decimal(fat),
                "carbs_g": _one_decimal(carbs),
                "protein_g_per_kg": float(protein_rate),
                "protein_reference_min_g_per_kg": float(protein_min),
                "protein_reference_max_g_per_kg": float(protein_max),
                "protein_min_g": _one_decimal(weight * protein_min),
                "protein_max_g": _one_decimal(weight * protein_max),
                "protein_energy_percent": _one_decimal(protein_energy / calories * 100),
                "fat_energy_percent": _one_decimal(fat_energy / calories * 100),
                "carbs_energy_percent": _one_decimal(carbs_energy / calories * 100),
            })
    result["status"] = "needs_review" if reasons else "estimated"
    if reasons:
        notes.append("当前资料尚未确认适用范围或超出本工具自动生成目标的范围，"
                     "已保留资料但不显示热量与营养目标。")
    return result
