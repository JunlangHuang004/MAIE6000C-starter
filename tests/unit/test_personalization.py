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
}
TARGET_KEYS = ("calories", "protein_g", "fat_g", "carbs_g")


def reference(**changes):
    return personalization.calculate_reference(SimpleNamespace(**{**PROFILE, **changes}))


def test_known_male_gain_example_has_independently_calculated_values():
    result = reference()
    # 700 + 1093.75 - 150 + 5 = 1648.75; x 1.55 x 1.05 = 2683.340625.
    assert result["resting_kcal"] == 1648.8
    assert result["maintenance_kcal"] == 2555.6
    assert result["calories"] == 2680
    assert result["protein_g"] == 167.5
    assert result["fat_g"] == 89.3
    assert result["carbs_g"] == 301.5
    assert result["bmi"] == 22.9
    assert result["activity_factor"] == 1.55
    assert result["goal_adjustment"] == 0.05
    assert result["status"] == "estimated"
    assert result["reason_codes"] == []
    assert result["formula_version"] == "mifflin-1990-nutrichat-v1"
    assert result["notes"] and all(isinstance(note, str) for note in result["notes"])


def test_known_female_loss_example_and_half_up_macro_rounding():
    result = reference(sex="female", goal="lose_fat")
    # 700 + 1093.75 - 150 - 161 = 1482.75; x 1.55 x .9 = 2068.43625.
    assert result["resting_kcal"] == 1482.8
    assert result["maintenance_kcal"] == 2298.3
    assert result["calories"] == 2070
    assert result["protein_g"] == 129.4
    assert result["fat_g"] == 69.0
    assert result["carbs_g"] == 232.9
    assert result["goal_adjustment"] == -0.1
    assert result["status"] == "estimated"


@pytest.mark.parametrize("sex", ["male", "female"])
@pytest.mark.parametrize("activity", ["sedentary", "light", "moderate", "high"])
def test_goals_are_either_side_of_maintenance_and_macros_reconcile(sex, activity):
    gain = reference(sex=sex, activity_level=activity)
    loss = reference(sex=sex, activity_level=activity, goal="lose_fat")
    assert gain["calories"] > gain["maintenance_kcal"] > loss["calories"]
    for result in (gain, loss):
        assert result["status"] == "estimated"
        energy = 4 * result["protein_g"] + 9 * result["fat_g"] + 4 * result["carbs_g"]
        # Independent one-decimal macro rounding can introduce at most 0.85 kcal.
        assert abs(energy - result["calories"]) <= 0.851
        assert result["calories"] % 10 == 0


def test_activity_increases_maintenance_and_target_without_changing_resting_energy():
    results = [reference(activity_level=level) for level in (
        "sedentary", "light", "moderate", "high",
    )]
    assert [row["activity_factor"] for row in results] == [1.2, 1.375, 1.55, 1.725]
    assert len({row["resting_kcal"] for row in results}) == 1
    assert all(first["calories"] < second["calories"] for first, second in zip(
        results, results[1:],
    ))


@pytest.mark.parametrize("weight,expected", [(141.999, 3460), (142, 3470), (142.001, 3470)])
def test_calorie_rounding_at_exact_five_is_half_up(weight, expected):
    # At 142 kg: resting 2400; light activity x 1.375 x 1.05 = exactly 3465.
    result = reference(weight_kg=weight, height_cm=180, activity_level="light")
    assert result["calories"] == expected


def test_underweight_fat_loss_uses_unrounded_bmi_and_withholds_all_targets():
    blocked = reference(height_cm=200, weight_kg=73.999, goal="lose_fat")
    boundary = reference(height_cm=200, weight_kg=74, goal="lose_fat")
    assert blocked["bmi"] == boundary["bmi"] == 18.5
    assert blocked["status"] == "needs_review"
    assert blocked["reason_codes"] == ["underweight_fat_loss"]
    assert all(blocked[key] is None for key in TARGET_KEYS)
    assert boundary["status"] == "estimated"
    assert all(boundary[key] is not None for key in TARGET_KEYS)


def test_underweight_alone_does_not_block_a_gain_reference():
    result = reference(height_cm=200, weight_kg=60, goal="gain_muscle")
    assert result["bmi"] < 18.5
    assert result["status"] == "estimated"


@pytest.mark.parametrize("sex,below,above,limit", [
    ("male", 84.63, 84.64, 1500),
    ("female", 73.46, 73.47, 1200),
])
def test_energy_guard_checks_before_rounding_and_does_not_silently_clamp(
        sex, below, above, limit):
    changes = {
        "age_years": 80, "height_cm": 150, "sex": sex,
        "goal": "lose_fat", "activity_level": "sedentary",
    }
    blocked = reference(**changes, weight_kg=below)
    allowed = reference(**changes, weight_kg=above)
    assert blocked["status"] == "needs_review"
    assert blocked["reason_codes"] == ["low_energy_reference"]
    assert all(blocked[key] is None for key in TARGET_KEYS)
    assert allowed["status"] == "estimated"
    assert allowed["calories"] == limit


def test_multiple_guard_reasons_are_retained_and_inputs_are_not_rewritten():
    profile = SimpleNamespace(**{
        **PROFILE, "weight_kg": 30, "height_cm": 175, "age_years": 80,
        "goal": "lose_fat", "activity_level": "sedentary",
    })
    before = vars(profile).copy()
    result = personalization.calculate_reference(profile)
    assert result["reason_codes"] == ["underweight_fat_loss", "low_energy_reference"]
    assert all(result[key] is None for key in TARGET_KEYS)
    assert vars(profile) == before


def test_resting_guard_still_applies_if_a_future_activity_assumption_changes(monkeypatch):
    monkeypatch.setitem(personalization.ACTIVITY_FACTORS, "sedentary", Decimal("0.9"))
    result = reference(activity_level="sedentary")
    assert result["reason_codes"] == ["below_resting_reference"]
    assert all(result[key] is None for key in TARGET_KEYS)


@pytest.mark.parametrize("field,value", [
    ("age_years", 17), ("age_years", 81), ("age_years", 30.0), ("age_years", True),
    ("age_years", "30"), ("height_cm", 119.9), ("height_cm", 220.1),
    ("height_cm", "175"), ("height_cm", True), ("weight_kg", 29.9),
    ("weight_kg", 250.1), ("weight_kg", "70"), ("weight_kg", False),
    ("sex", "other"), ("sex", 1), ("goal", "maintain"),
    ("goal", None), ("activity_level", "extreme"), ("revision", -1),
    ("revision", True), ("revision", "0"), ("revision", 0.0),
    ("revision", 2**63),
])
def test_profile_schema_rejects_out_of_scope_values_and_type_coercion(field, value):
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate({**PROFILE, "revision": 0, field: value})


@pytest.mark.parametrize("field", ["height_cm", "weight_kg"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_profile_schema_rejects_nonfinite_measurements(field, value):
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate({**PROFILE, "revision": 0, field: value})


@pytest.mark.parametrize("missing", [*PROFILE, "revision"])
def test_every_profile_input_is_required(missing):
    values = {**PROFILE, "revision": 0}
    del values[missing]
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate(values)


@pytest.mark.parametrize("changes", [
    {"age_years": 18, "height_cm": 120, "weight_kg": 30},
    {"age_years": 80, "height_cm": 220, "weight_kg": 250},
])
def test_profile_schema_accepts_inclusive_boundaries_and_integer_measurements(changes):
    profile = ProfileUpdate.model_validate({**PROFILE, "revision": 0, **changes})
    assert profile.age_years == changes["age_years"]
    assert profile.height_cm == changes["height_cm"]
    assert profile.weight_kg == changes["weight_kg"]
