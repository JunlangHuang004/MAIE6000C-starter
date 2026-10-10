from services.ai.app.main import analyze_nutrition_text, triage_text


def test_triage_access_case():
    result = triage_text(
        "Cannot login",
        "User cannot access the dashboard after a password reset.",
    )
    assert result.label == "access"
    assert result.confidence >= 0.55
    assert "Cannot login" in result.summary


def test_triage_general_case():
    result = triage_text(
        "General question",
        "Need clarification about the process for next week.",
    )
    assert result.label == "general"


def test_analyze_nutrition_for_known_foods():
    result = analyze_nutrition_text("200g chicken breast and 230g cooked white rice")

    assert result.calories == 629.0
    assert result.protein_g == 68.2
    assert result.carbs_g == 64.4
    assert result.fat_g == 7.9
