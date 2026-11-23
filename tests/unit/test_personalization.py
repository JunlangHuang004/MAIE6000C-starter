"""Independent numerical examples and boundaries of the adult reference calculator."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from services.common import personalization
from services.common.schemas import ProfileUpdate


PROFILE = {
    "age_years": 30,
    "height_cm": 175,
    "weight_kg": 70,
    "sex": "male",
    "goal": "gain_muscle",
    "activity_level": "moderate",
    "strength_training": True,
    "reference_scope": "general_adult",
}
OPTIONAL_FIELDS = ("strength_training", "reference_scope")
TARGET_KEYS = (
    "calories", "protein_g", "fat_g", "carbs_g", "protein_g_per_kg",
    "protein_reference_min_g_per_kg", "protein_reference_max_g_per_kg",
    "protein_min_g", "protein_max_g", "protein_energy_percent",
    "fat_energy_percent", "carbs_energy_percent",
)


def reference(**changes):
    return personalization.calculate_reference(SimpleNamespace(**{**PROFILE, **changes}))


def assert_withheld(result, reasons):
    assert result["status"] == "needs_review"
    assert result["reason_codes"] == reasons
    assert all(result[key] is None for key in TARGET_KEYS)


def test_known_male_gain_example_has_independently_calculated_values():
    result = reference()
    # Resting 1648.75; maintenance 2555.5625; +5% = 2683.340625 -> 2680.
    # Actual-weight protein 70*1.6=112; fat 804/9; residual carbs 1428/4.
    assert result["resting_kcal"] == 1648.8
    assert result["maintenance_kcal"] == 2555.6
    assert result["calories"] == 2680
    assert result["protein_g"] == 112.0
    assert result["fat_g"] == 89.3
    assert result["carbs_g"] == 357.0
    assert result["bmi"] == 22.9
    assert result["activity_factor"] == 1.55
    assert result["goal_adjustment"] == 0.05
    assert result["energy_adjustment_kcal"] == 127.8
    assert result["protein_g_per_kg"] == result["protein_reference_min_g_per_kg"] == 1.6
    assert result["protein_reference_max_g_per_kg"] == 2.2
    assert (result["protein_min_g"], result["protein_max_g"]) == (112.0, 154.0)
    assert [result[key] for key in (
        "protein_energy_percent", "fat_energy_percent", "carbs_energy_percent",
    )] == [16.7, 30.0, 53.3]
    assert result["status"] == "estimated"
    assert result["reason_codes"] == []
    assert result["formula_version"] == "mifflin-evidence-2026-v2"


def test_known_female_trained_loss_reduces_fat_to_preserve_carbohydrate_share():
    result = reference(sex="female", goal="lose_fat")
    # Resting 1482.75; maintenance 2298.2625; -15% = 1953.523125 -> 1950.
    # Protein 126g = 504kcal; fat 55%*1950-504=568.5kcal; carbs 877.5/4.
    assert result["resting_kcal"] == 1482.8
    assert result["maintenance_kcal"] == 2298.3
    assert result["calories"] == 1950
    assert result["protein_g"] == 126.0
    assert result["fat_g"] == 63.2
    assert result["carbs_g"] == 219.4
    assert result["goal_adjustment"] == -0.15
    assert result["energy_adjustment_kcal"] == -344.7
    assert result["protein_g_per_kg"] == 1.8
    assert (result["protein_min_g"], result["protein_max_g"]) == (112.0, 154.0)
    assert [result[key] for key in (
        "protein_energy_percent", "fat_energy_percent", "carbs_energy_percent",
    )] == [25.8, 29.2, 45.0]
    assert result["status"] == "estimated"


def test_untrained_loss_has_distinct_protein_reference_and_same_energy_policy():
    result = reference(sex="female", goal="lose_fat", strength_training=False)
    assert result["calories"] == 1950
    assert (result["protein_g"], result["fat_g"], result["carbs_g"]) == (98.0, 65.0, 243.3)
    assert result["protein_g_per_kg"] == 1.4
    assert result["protein_reference_min_g_per_kg"] == 1.2
    assert result["protein_reference_max_g_per_kg"] == 1.6
    assert (result["protein_min_g"], result["protein_max_g"]) == (84.0, 112.0)


@pytest.mark.parametrize("sex", ["male", "female"])
@pytest.mark.parametrize("activity", ["sedentary", "light", "moderate", "high"])
@pytest.mark.parametrize("goal,training,protein", [
    ("gain_muscle", True, 112.0), ("lose_fat", True, 126.0), ("lose_fat", False, 98.0),
])
def test_profile_matrix_has_consistent_energy_macros_and_weight_based_protein(
        sex, activity, goal, training, protein):
    result = reference(sex=sex, activity_level=activity, goal=goal, strength_training=training)
    assert result["status"] == "estimated"
    assert (result["calories"] > result["maintenance_kcal"]) == (goal == "gain_muscle")
    assert result["protein_g"] == protein
    assert 10 <= result["protein_energy_percent"] <= 35
    assert 20 <= result["fat_energy_percent"] <= 30
    assert 45 <= result["carbs_energy_percent"] <= 65
    assert result["carbs_g"] >= 130
    energy = sum(Decimal(str(result[key])) * factor for key, factor in (
        ("protein_g", 4), ("fat_g", 9), ("carbs_g", 4),
    ))
    # Independent one-decimal macro rounding can introduce at most 0.85 kcal.
    assert abs(energy - result["calories"]) <= Decimal("0.85")
    assert result["calories"] % 10 == 0


def test_large_maintenance_caps_deficit_and_reports_actual_signed_fraction():
    result = reference(goal="lose_fat", weight_kg=110, height_cm=190, activity_level="high")
    # Resting 2142.5; maintenance 3695.8125; subtract 500 -> 3195.8125 -> 3200.
    assert result["status"] == "estimated"
    assert result["maintenance_kcal"] == 3695.8
    assert result["calories"] == 3200
    assert result["energy_adjustment_kcal"] == -500.0
    assert result["goal_adjustment"] == pytest.approx(-500 / 3695.8125)
    assert -0.15 < result["goal_adjustment"] < 0
    assert result["protein_g"] == 198.0  # Actual 110kg, without an adjusted-weight formula.


def test_deficit_cap_compares_unrounded_maintenance():
    below = reference(goal="lose_fat", weight_kg=120.178)
    above = reference(goal="lose_fat", weight_kg=120.179)
    assert below["status"] == above["status"] == "estimated"
    assert below["maintenance_kcal"] == above["maintenance_kcal"] == 3333.3
    assert below["goal_adjustment"] == -0.15
    assert above["goal_adjustment"] > -0.15
    assert above["energy_adjustment_kcal"] == -500


def test_activity_increases_energy_without_changing_weight_based_protein():
    results = [reference(activity_level=level) for level in (
        "sedentary", "light", "moderate", "high",
    )]
    assert [row["activity_factor"] for row in results] == [1.2, 1.375, 1.55, 1.725]
    assert len({row["resting_kcal"] for row in results}) == 1
    assert len({row["protein_g"] for row in results}) == 1
    assert all(first["calories"] < second["calories"] for first, second in zip(
        results, results[1:],
    ))


@pytest.mark.parametrize("weight,expected", [(129.499, 3460), (129.5, 3470), (129.501, 3470)])
def test_calorie_rounding_at_exact_five_is_half_up(weight, expected):
    # At 129.5kg and 200cm: resting 2400; light activity x1.375 x1.05 = 3465.
    result = reference(weight_kg=weight, height_cm=200, activity_level="light")
    assert result["calories"] == expected


def test_macros_are_rounded_independently_after_residual_energy_is_calculated():
    result = reference(weight_kg=70.03125)
    # Protein 112.05g rounds up, but residual carbs use that unrounded amount:
    # (2680 - 112.05*4 - 804)/4 = 356.95g, also rounded half up.
    assert result["calories"] == 2680
    assert result["protein_g"] == 112.1
    assert result["fat_g"] == 89.3
    assert result["carbs_g"] == 357.0


@pytest.mark.parametrize("goal", ["gain_muscle", "lose_fat"])
def test_underweight_guard_applies_to_both_goals_before_bmi_rounding(goal):
    blocked = reference(height_cm=200, weight_kg=73.999, goal=goal)
    boundary = reference(height_cm=200, weight_kg=74, goal=goal)
    assert blocked["bmi"] == boundary["bmi"] == 18.5
    assert_withheld(blocked, ["underweight_reference"])
    assert boundary["status"] == "estimated"


@pytest.mark.parametrize("goal", ["gain_muscle", "lose_fat"])
def test_high_bmi_scope_includes_exact_boundary_for_both_goals(goal):
    below = reference(weight_kg=122.499, goal=goal)
    boundary = reference(weight_kg=122.5, goal=goal)
    assert below["bmi"] == boundary["bmi"] == 40.0
    assert below["status"] == "estimated"
    assert_withheld(boundary, ["high_bmi_reference"])


@pytest.mark.parametrize("changes,reasons", [
    ({"reference_scope": None}, ["scope_confirmation_required"]),
    ({"reference_scope": "professional_guidance"}, ["professional_guidance_required"]),
    ({"strength_training": None}, ["training_confirmation_required"]),
    ({"strength_training": False}, ["strength_training_required"]),
    ({"reference_scope": None, "strength_training": None},
     ["scope_confirmation_required", "training_confirmation_required"]),
])
def test_confirmation_and_applicability_guards_withhold_all_target_metadata(changes, reasons):
    assert_withheld(reference(**changes), reasons)


def test_legacy_profile_without_new_attributes_requires_confirmation():
    profile = SimpleNamespace(**{key: value for key, value in PROFILE.items()
                                 if key not in OPTIONAL_FIELDS})
    result = personalization.calculate_reference(profile)
    assert_withheld(result, ["scope_confirmation_required", "training_confirmation_required"])


@pytest.mark.parametrize("sex,below,above,limit", [
    ("male", 67.808, 67.809, 1500),
    ("female", 54.997, 54.998, 1200),
])
def test_energy_guard_checks_before_rounding_and_does_not_silently_clamp(
        sex, below, above, limit):
    changes = {
        "height_cm": 150, "sex": sex, "goal": "lose_fat", "activity_level": "sedentary",
    }
    blocked = reference(**changes, weight_kg=below)
    allowed = reference(**changes, weight_kg=above)
    assert_withheld(blocked, ["low_energy_reference"])
    assert allowed["status"] == "estimated"
    assert allowed["calories"] == limit


def test_multiple_guard_reasons_are_retained_and_inputs_are_not_rewritten():
    profile = SimpleNamespace(**{
        **PROFILE, "weight_kg": 30, "height_cm": 175, "age_years": 80,
        "goal": "lose_fat", "activity_level": "sedentary", "reference_scope": None,
        "strength_training": None,
    })
    before = vars(profile).copy()
    result = personalization.calculate_reference(profile)
    assert_withheld(result, ["scope_confirmation_required", "training_confirmation_required",
                             "underweight_reference", "low_energy_reference"])
    assert vars(profile) == before


def test_resting_guard_still_applies_if_a_future_activity_assumption_changes(monkeypatch):
    monkeypatch.setitem(personalization.ACTIVITY_FACTORS, "sedentary", Decimal("0.9"))
    assert_withheld(reference(activity_level="sedentary"), ["below_resting_reference"])


def test_exact_adult_macro_boundary_is_allowed_but_unrounded_excess_is_withheld():
    # At 70kg: rounded energy 1440; protein 126g = 35%; fat20%; carbs45%.
    changes = {"sex": "female", "height_cm": 164, "goal": "lose_fat",
               "activity_level": "sedentary"}
    boundary = reference(**changes)
    assert boundary["status"] == "estimated"
    assert boundary["protein_energy_percent"] == 35
    assert boundary["fat_energy_percent"] == 20
    assert boundary["carbs_energy_percent"] == 45
    assert_withheld(reference(**changes, weight_kg=70.001), ["macro_distribution_out_of_scope"])


def test_eighteen_year_old_uses_age_specific_fat_and_protein_limits():
    # At 18y/70kg: rounded energy1680; protein126g=30%; fat25%; carbs45%.
    changes = {"age_years": 18, "sex": "female", "height_cm": 192,
               "goal": "lose_fat", "activity_level": "sedentary"}
    boundary = reference(**changes)
    assert boundary["status"] == "estimated"
    assert boundary["protein_energy_percent"] == 30
    assert boundary["fat_energy_percent"] == 25
    assert boundary["carbs_energy_percent"] == 45
    assert_withheld(reference(**changes, weight_kg=70.001), ["macro_distribution_out_of_scope"])
    adult = reference(**{**changes, "age_years": 19}, weight_kg=70.001)
    assert adult["status"] == "estimated"


def test_carbohydrate_gram_guard_survives_a_future_energy_minimum_change(monkeypatch):
    monkeypatch.setitem(personalization.AUTOMATIC_ENERGY_MINIMUM, "female", Decimal("1000"))
    # Rounded energy1040 leaves117g carbs despite acceptable energy shares.
    result = reference(sex="female", age_years=80, height_cm=150, weight_kg=45,
                       activity_level="sedentary")
    assert_withheld(result, ["macro_distribution_out_of_scope"])


def test_estimates_and_withheld_references_both_explain_evidence_and_product_choices():
    for result in (reference(), reference(reference_scope=None)):
        assert 6 <= len(result["sources"]) <= 8
        assert all(source["title"] and source["url"].startswith("https://")
                   for source in result["sources"])
        notes = " ".join(result["notes"])
        assert "起始策略" in notes and "30% 是分配选择" in notes
        assert "2–4 周" in notes and "不会" in notes


@pytest.mark.parametrize("field,value", [
    ("age_years", 17), ("age_years", 81), ("age_years", 30.0), ("age_years", True),
    ("age_years", "30"), ("height_cm", 119.9), ("height_cm", 220.1),
    ("height_cm", "175"), ("height_cm", True), ("weight_kg", 29.9),
    ("weight_kg", 250.1), ("weight_kg", "70"), ("weight_kg", False),
    ("sex", "other"), ("sex", 1), ("goal", "maintain"),
    ("goal", None), ("activity_level", "extreme"), ("revision", -1),
    ("revision", True), ("revision", "0"), ("revision", 0.0),
    ("revision", 2**63), ("strength_training", "false"), ("strength_training", 1),
    ("reference_scope", "unknown"), ("reference_scope", True),
])
def test_profile_schema_rejects_out_of_scope_values_and_type_coercion(field, value):
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate({**PROFILE, "revision": 0, field: value})


@pytest.mark.parametrize("field", ["height_cm", "weight_kg"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_profile_schema_rejects_nonfinite_measurements(field, value):
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate({**PROFILE, "revision": 0, field: value})


@pytest.mark.parametrize("missing", [key for key in PROFILE if key not in OPTIONAL_FIELDS] +
                         ["revision"])
def test_original_profile_inputs_remain_required(missing):
    values = {**PROFILE, "revision": 0}
    del values[missing]
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate(values)


def test_new_optional_schema_fields_default_to_unconfirmed_not_assumed_healthy():
    values = {key: value for key, value in PROFILE.items() if key not in OPTIONAL_FIELDS}
    profile = ProfileUpdate.model_validate({**values, "revision": 0})
    assert profile.reference_scope is None
    assert profile.strength_training is None
    assert_withheld(personalization.calculate_reference(profile),
                    ["scope_confirmation_required", "training_confirmation_required"])


@pytest.mark.parametrize("changes", [
    {"age_years": 18, "height_cm": 120, "weight_kg": 30},
    {"age_years": 80, "height_cm": 220, "weight_kg": 250},
])
def test_profile_schema_accepts_inclusive_boundaries_and_integer_measurements(changes):
    profile = ProfileUpdate.model_validate({**PROFILE, "revision": 0, **changes})
    assert profile.age_years == changes["age_years"]
    assert profile.height_cm == changes["height_cm"]
    assert profile.weight_kg == changes["weight_kg"]
