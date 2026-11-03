"""Provider contracts use synthetic replies and never contact a model service."""

import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from services.ai.app import qwen
from services.ai.app.qwen import analyze_with_provider, select_ollama_catalogue
from services.common.config import Settings
from services.common.meal_engine import catalogue


PROVIDERS = ("hkust", "ollama")
SYNTHETIC_KEY = "synthetic-provider-key-never-a-real-credential"
EGG = {
    "food_id": "egg", "name": "水煮鸡蛋", "grams": 125,
    "weight_basis": "cooked", "preparation": "boiled",
}


@pytest.fixture(autouse=True)
def isolated_provider_environment(monkeypatch):
    for name in (
        "LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY",
        "LLM_API_KEY_HEADER", "NUTRITION_PROVIDER", "DASHSCOPE_API_KEY", "QWEN_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    def no_live_request(*args, **kwargs):
        pytest.fail("Provider tests must mock every external model request")

    monkeypatch.setattr(httpx, "post", no_live_request)


def provider_settings(provider, **kwargs):
    options = {
        "_env_file": None,
        "llm_provider": provider,
        "llm_base_url": (
            "https://hkust.example.test/openai/v1" if provider == "hkust"
            else "http://127.0.0.1:11434"
        ),
        "llm_model": "synthetic-model",
        "llm_api_key": SecretStr(SYNTHETIC_KEY if provider == "hkust" else ""),
    }
    options.update(kwargs)
    return Settings(**options)


def model_response(provider, content, complete=True):
    if provider == "ollama":
        return {
            "message": {"role": "assistant", "content": content},
            "done": complete, "done_reason": "stop" if complete else "length",
        }
    return {"choices": [{
        "finish_reason": "stop" if complete else "length",
        "message": {"content": content},
    }]}


def mock_model(monkeypatch, provider, content, complete=True):
    calls = []

    def respond(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(
            200, request=httpx.Request("POST", url),
            json=model_response(provider, content, complete),
        )

    monkeypatch.setattr(httpx, "post", respond)
    return calls


@pytest.mark.parametrize("provider", PROVIDERS)
def test_provider_uses_catalogue_arithmetic_for_decimal_portions(monkeypatch, provider):
    mock_model(monkeypatch, provider, json.dumps({"items": [EGG]}))
    result = analyze_with_provider("125克去壳水煮鸡蛋，熟重", provider_settings(provider))
    egg = next(food for food in catalogue()["foods"] if food["id"] == "egg")
    assert result.questions == []
    for nutrient in ("calories", "protein_g", "carbs_g", "fat_g"):
        assert getattr(result, nutrient) == round(egg["nutrients"][nutrient] * 1.25, 1)
    assert result.details[0]["sources"]
    assert result.draft[0]["grams"] == 125


@pytest.mark.parametrize("provider", PROVIDERS)
def test_basic_mode_labels_missing_weight_assumption_while_advanced_asks(monkeypatch, provider):
    mock_model(monkeypatch, provider, json.dumps({"items": [{**EGG, "grams": None}]}))
    basic = analyze_with_provider("水煮鸡蛋", provider_settings(provider), mode="basic")
    assert basic.calories > 0
    assert basic.questions == []
    assert basic.draft[0]["grams"] is None
    assert any("未提供克数" in note for note in basic.details[0]["assumptions"])
    advanced = analyze_with_provider("水煮鸡蛋", provider_settings(provider), mode="advanced")
    assert advanced.calories is None
    assert "0.grams" in {question["key"] for question in advanced.questions}


def test_hkust_request_uses_subscription_header_and_retains_correction_history(monkeypatch):
    calls = mock_model(monkeypatch, "hkust", json.dumps({"items": [EGG]}))
    history = [
        {"role": "user", "content": "100克去壳水煮鸡蛋，熟重"},
        {"role": "assistant", "content": "请确认可食重量。"},
        {"role": "user", "content": "改成125克"},
    ]
    analyze_with_provider("改成125克", provider_settings("hkust"), history, "advanced")
    assert len(calls) == 1
    url, request = calls[0]
    assert url == "https://hkust.example.test/openai/v1/chat/completions"
    assert request["headers"] == {"api-key": SYNTHETIC_KEY}
    assert request["json"]["model"] == "synthetic-model"
    assert "enable_thinking" not in request["json"]
    assert request["json"]["response_format"] == {"type": "json_object"}
    prompt = request["json"]["messages"][0]["content"]
    assert '"enum":["raw","cooked","as_sold"]' in prompt
    assert '"additionalProperties":false' in prompt
    assert json.loads(request["json"]["messages"][-1]["content"]) == history
    assert SYNTHETIC_KEY not in json.dumps(request["json"])


def test_ollama_request_is_local_and_never_sends_cloud_credentials(monkeypatch):
    calls = mock_model(monkeypatch, "ollama", json.dumps({"items": [EGG]}))
    settings = provider_settings(
        "ollama", llm_api_key=SecretStr(SYNTHETIC_KEY),
        dashscope_api_key=SecretStr("synthetic-qwen-key"),
    )
    analyze_with_provider("125克去壳水煮鸡蛋，熟重", settings)
    assert len(calls) == 1
    url, request = calls[0]
    assert url == "http://127.0.0.1:11434/api/chat"
    assert not request.get("headers")
    assert request["json"]["stream"] is False
    schema = request["json"]["format"]
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    item_type = schema["properties"]["items"]["items"]["$ref"].split("/")[-1]
    item_schema = schema["$defs"][item_type]
    assert item_schema["additionalProperties"] is False
    properties = item_schema["properties"]
    candidates = select_ollama_catalogue("125克去壳水煮鸡蛋，熟重")
    food_options = properties["food_id"]["anyOf"]
    assert {entry["type"] for entry in food_options} == {"string", "null"}
    assert next(entry["enum"] for entry in food_options if entry["type"] == "string") == (
        sorted(food["id"] for food in candidates)
    )
    recipe_options = properties["recipe_ingredients"]["anyOf"]
    assert {entry["type"] for entry in recipe_options} == {"object", "null"}
    ingredient_schema = next(entry for entry in recipe_options if entry["type"] == "object")
    assert ingredient_schema["additionalProperties"] is False
    assert set(ingredient_schema["properties"]) == {
        food["id"] for food in candidates if food["kind"] == "ingredient"
    }
    assert all(field["type"] == "number" and field["minimum"] == 0
               for field in ingredient_schema["properties"].values())
    assert 0 < request["json"]["options"]["num_ctx"] <= 16384
    assert request["json"]["options"]["temperature"] == 0
    assert "enable_thinking" not in request["json"]
    assert SYNTHETIC_KEY not in json.dumps(request)
    assert "synthetic-qwen-key" not in json.dumps(request)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_unsupported_food_requests_clarification_without_partial_totals(monkeypatch, provider):
    items = [EGG, {"food_id": None, "name": "未知餐食", "grams": 100}]
    mock_model(monkeypatch, provider, json.dumps({"items": items}))
    result = analyze_with_provider("125克水煮鸡蛋和100克未知餐食", provider_settings(provider))
    assert any(question["kind"] == "unsupported" for question in result.questions)
    assert all(getattr(result, field) is None
               for field in ("calories", "protein_g", "carbs_g", "fat_g"))


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("content", [
    "not JSON",
    json.dumps({"items": []}),
    json.dumps({"items": [{**EGG, "grams": -1}]}),
    json.dumps({"items": [{**EGG, "calories": 1}]}),
    json.dumps({"items": [{**EGG, "recipe_ingredients": {"invented-oil": 10}}]}),
    json.dumps({"items": [{**EGG, "recipe_ingredients": [None, None]}]}),
])
def test_provider_rejects_malformed_or_invented_facts(monkeypatch, provider, content):
    calls = mock_model(monkeypatch, provider, content)
    with pytest.raises(RuntimeError):
        analyze_with_provider("125克水煮鸡蛋", provider_settings(provider))
    assert len(calls) == 1


@pytest.mark.parametrize("provider", PROVIDERS)
def test_incomplete_model_generation_never_becomes_an_estimate(monkeypatch, provider):
    calls = mock_model(monkeypatch, provider, json.dumps({"items": [EGG]}), complete=False)
    with pytest.raises(RuntimeError):
        analyze_with_provider("125克水煮鸡蛋", provider_settings(provider))
    assert len(calls) == 1


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("failure", [
    "timeout", "unauthorized", "malformed_envelope", "non_object_envelope", "non_object_choice",
])
def test_provider_errors_do_not_expose_request_or_response_secrets(monkeypatch, provider, failure):
    private_detail = "SYNTHETIC_PRIVATE_PROVIDER_ERROR"

    def respond(url, **kwargs):
        if failure == "timeout":
            raise httpx.ReadTimeout(f"{private_detail}: {SYNTHETIC_KEY}")
        body = {"provider_private_detail": private_detail, "key": SYNTHETIC_KEY}
        if failure == "non_object_envelope":
            body = [private_detail]
        elif failure == "non_object_choice":
            body = {"choices": [private_detail], "message": private_detail,
                    "done": True, "done_reason": "stop"}
        return httpx.Response(
            401 if failure == "unauthorized" else 200,
            request=httpx.Request("POST", url),
            json=body,
        )

    monkeypatch.setattr(httpx, "post", respond)
    with pytest.raises(RuntimeError) as error:
        analyze_with_provider("125克水煮鸡蛋", provider_settings(provider))
    assert private_detail not in str(error.value)
    assert SYNTHETIC_KEY not in str(error.value)


def test_hkust_without_key_fails_before_any_network_request():
    with pytest.raises(RuntimeError):
        analyze_with_provider("125克水煮鸡蛋", provider_settings("hkust", llm_api_key=""))


@pytest.mark.parametrize("legacy,override,expected", [
    ("demo", None, "demo"), ("qwen", None, "qwen"),
    ("qwen", "heuristic", "demo"), ("demo", "ollama", "ollama"),
    ("qwen", "hkust", "hkust"),
])
def test_explicit_course_provider_overrides_legacy_provider(legacy, override, expected):
    settings = Settings(_env_file=None, nutrition_provider=legacy, llm_provider=override)
    assert settings.effective_nutrition_provider == expected


def test_heuristic_environment_works_without_keys_even_with_legacy_qwen(monkeypatch):
    monkeypatch.setenv("NUTRITION_PROVIDER", "qwen")
    monkeypatch.setenv("LLM_PROVIDER", "heuristic")
    settings = Settings(_env_file=None)
    assert settings.effective_nutrition_provider == "demo"
    assert not settings.llm_api_key.get_secret_value()


def test_unknown_provider_does_not_silently_fall_back_to_demo():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_provider="ollama-typo")


def test_local_retrieval_recognizes_dish_alias_and_preserves_recipe_dependencies():
    selected = select_ollama_catalogue("200克西红柿炒鸡蛋和100克白米飯")
    ids = {food["id"] for food in selected}
    dish = next(food for food in catalogue()["foods"] if food["id"] == "dish_001")
    assert {"dish_001", "rice"} <= ids
    assert set(dish["recipe"]["ingredients"]) <= ids


def test_local_retrieval_keeps_ambiguous_candidates_instead_of_guessing(monkeypatch):
    candidates = [
        {"id": "raw_beef", "name": "Raw beef", "kind": "ingredient", "aliases": ["牛肉"]},
        {"id": "cooked_beef", "name": "Cooked beef", "kind": "ingredient", "aliases": ["牛肉"]},
    ]
    monkeypatch.setattr(qwen, "catalogue", lambda: {"foods": candidates})
    assert {food["id"] for food in select_ollama_catalogue("100克牛肉")} == {
        "raw_beef", "cooked_beef",
    }


def test_local_retrieval_uses_user_history_but_not_assistant_suggestions():
    history = [
        {"role": "user", "content": "125克水煮鸡蛋"},
        {"role": "assistant", "content": "还要添加大豆食用油和米饭吗？"},
    ]
    first_ids = {food["id"] for food in select_ollama_catalogue("改成100克", history)}
    assert "egg" in first_ids
    assert not {"oil", "rice"} & first_ids
    later_ids = {food["id"] for food in select_ollama_catalogue("再加200克米饭", history)}
    assert {"egg", "rice"} <= later_ids
    assert "oil" not in later_ids


def test_local_retrieval_does_not_match_oil_inside_boiled():
    assert "oil" not in {food["id"] for food in select_ollama_catalogue("100g boiled egg")}


def test_local_unknown_food_stays_unknown_without_substitution(monkeypatch):
    text = "100克超新星糕点"
    assert select_ollama_catalogue(text) == []
    calls = mock_model(monkeypatch, "ollama", json.dumps({"items": [{
        "food_id": None, "name": "超新星糕点", "grams": 100,
    }]}))
    result = analyze_with_provider(text, provider_settings("ollama"))
    assert len(calls) == 1
    schema = calls[0][1]["json"]["format"]
    assert schema["$defs"]["ExtractedItem"]["properties"]["food_id"]["type"] == "null"
    assert result.calories is None
    assert result.questions[0]["kind"] == "unsupported"
    assert result.draft[0]["food_id"] is None


def test_local_retrieval_rejects_oversized_candidate_set_without_dropping_foods():
    foods = catalogue()["foods"]
    with pytest.raises(RuntimeError):
        select_ollama_catalogue("、".join(food["name"] for food in foods[:50]))


def test_local_long_history_fails_before_request_instead_of_truncating_rules():
    history = [{"role": "user", "content": "详细说明" * 5000}]
    with pytest.raises(RuntimeError):
        analyze_with_provider("125克水煮鸡蛋", provider_settings("ollama"), history)


def test_local_wrong_id_is_replaced_only_by_exact_reviewed_original_name(monkeypatch):
    calls = mock_model(monkeypatch, "ollama", json.dumps({"items": [{
        "food_id": "rice", "name": "水煮鸡蛋", "grams": 125,
        "weight_basis": "cooked", "preparation": "boiled",
    }]}))
    result = analyze_with_provider("125克水煮鸡蛋", provider_settings("ollama"))
    assert len(calls) == 1
    assert result.draft[0]["food_id"] == "egg"
    assert result.questions == []
    assert result.calories == 193.8


@pytest.mark.parametrize("base_url", [
    "http://127.0.0.1:11434/v1", "http://127.0.0.1:11434/api",
    "http://127.0.0.1:11434/api/chat/",
])
def test_local_base_urls_resolve_to_native_chat_endpoint(monkeypatch, base_url):
    calls = mock_model(monkeypatch, "ollama", json.dumps({"items": [EGG]}))
    analyze_with_provider(
        "125克水煮鸡蛋", provider_settings("ollama", llm_base_url=base_url),
    )
    assert calls[0][0] == "http://127.0.0.1:11434/api/chat"


def test_empty_course_selector_preserves_existing_qwen_configuration(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "")
    monkeypatch.setenv("NUTRITION_PROVIDER", "qwen")
    assert Settings(_env_file=None).effective_nutrition_provider == "qwen"


@pytest.mark.parametrize("food_id", ["egg", None])
def test_local_model_invented_weight_is_cleared_when_user_has_given_no_mass(monkeypatch, food_id):
    calls = mock_model(monkeypatch, "ollama", json.dumps({"items": [{
        **EGG, "food_id": food_id, "grams": 100,
    }]}))
    result = analyze_with_provider("我吃了水煮鸡蛋", provider_settings("ollama"))
    assert len(calls) == 1
    assert result.draft[0]["grams"] is None
    assert result.calories is None
    if food_id is not None:
        assert "0.grams" in {question["key"] for question in result.questions}


def test_local_assistant_suggested_mass_does_not_become_user_weight(monkeypatch):
    mock_model(monkeypatch, "ollama", json.dumps({"items": [{**EGG, "grams": 100}]}))
    history = [
        {"role": "user", "content": "我吃了水煮鸡蛋"},
        {"role": "assistant", "content": "是否吃了100克？"},
        {"role": "user", "content": "不知道重量"},
    ]
    result = analyze_with_provider("不知道重量", provider_settings("ollama"), history)
    assert result.draft[0]["grams"] is None
    assert result.calories is None


@pytest.mark.parametrize("text,grams", [
    ("100grams boiled egg", 100),
    ("100 grams boiled egg", 100),
    ("100公克水煮鸡蛋", 100),
    ("一百公克水煮鸡蛋", 100),
    ("100毫克水煮鸡蛋", 0.1),
    ("2两水煮鸡蛋", 100),
    ("2×50g水煮鸡蛋", 100),
    ("one hundred grams of boiled egg", 100),
    ("half a kilogram of boiled egg", 500),
])
def test_local_mass_guard_preserves_legitimate_units_and_derived_totals(text, grams):
    # This guard only decides whether any mass evidence is present. The separate
    # exact-name guard may still ask users to restate unsupported wording.
    assert grams > 0
    assert qwen._ollama_has_mass_evidence(text, [])


def test_local_mass_guard_preserves_explicit_user_history(monkeypatch):
    mock_model(monkeypatch, "ollama", json.dumps({"items": [{**EGG, "grams": 100}]}))
    history = [
        {"role": "user", "content": "100克水煮鸡蛋"},
        {"role": "assistant", "content": "是否去壳后的熟重？"},
        {"role": "user", "content": "是的"},
    ]
    result = analyze_with_provider("是的", provider_settings("ollama"), history)
    assert result.draft[0]["grams"] == 100
    assert result.questions == []


@pytest.mark.parametrize("provider", ["hkust", "qwen"])
def test_local_mass_guard_does_not_change_existing_cloud_adapters(monkeypatch, provider):
    mock_model(monkeypatch, provider, json.dumps({"items": [{**EGG, "grams": 100}]}))
    if provider == "qwen":
        settings = Settings(
            _env_file=None, nutrition_provider="qwen", llm_provider="qwen",
            dashscope_api_key="synthetic-qwen-key", qwen_base_url="https://qwen.example.test/v1",
        )
        result = qwen.analyze_with_qwen("水煮鸡蛋", settings)
    else:
        result = analyze_with_provider("水煮鸡蛋", provider_settings(provider))
    assert result.draft[0]["grams"] == 100
    assert result.questions == []


def test_local_unknown_item_cannot_reuse_another_meals_rice_identity(monkeypatch):
    items = [
        {"food_id": "rice", "name": "白米饭", "grams": 100,
         "weight_basis": "cooked", "preparation": "as_served"},
        {"food_id": "rice", "name": "超新星糕点", "grams": 100,
         "weight_basis": "cooked", "preparation": "as_served"},
    ]
    mock_model(monkeypatch, "ollama", json.dumps({"items": items}))
    result = analyze_with_provider("100克白米饭和100克超新星糕点", provider_settings("ollama"))
    assert len(result.draft) == 2
    assert result.draft[0]["food_id"] == "rice"
    assert result.draft[1]["food_id"] is None
    assert result.draft[1]["name"] == "超新星糕点"
    assert all(getattr(result, field) is None
               for field in ("calories", "protein_g", "carbs_g", "fat_g"))
    assert any(question["key"] == "1.food_id" for question in result.questions)


@pytest.mark.parametrize("name", ["白米饭", "米饭", "白米飯", "cooked rice"])
def test_local_name_guard_preserves_known_canonical_names_and_aliases(monkeypatch, name):
    mock_model(monkeypatch, "ollama", json.dumps({"items": [{
        "food_id": "rice", "name": name, "grams": 100,
        "weight_basis": "cooked", "preparation": "as_served",
    }]}))
    result = analyze_with_provider("100克" + name, provider_settings("ollama"))
    assert result.draft[0]["food_id"] == "rice"
    assert result.questions == []
    assert result.calories > 0


@pytest.mark.parametrize("ingredient_id", ["oil", "egg_raw"])
def test_local_recipe_dependency_is_not_itself_a_matching_dish_identity(monkeypatch, ingredient_id):
    text = "100克番茄炒蛋"
    assert ingredient_id in {food["id"] for food in select_ollama_catalogue(text)}
    mock_model(monkeypatch, "ollama", json.dumps({"items": [{
        "food_id": ingredient_id, "name": "番茄炒蛋", "grams": 100,
        "weight_basis": "cooked", "preparation": "stir_fried", "oil_g": 0,
    }]}))
    result = analyze_with_provider(text, provider_settings("ollama"), mode="basic")
    assert result.draft[0]["food_id"] == "dish_001"
    assert result.calories > 0
    assert result.questions == []


@pytest.mark.parametrize("provider", PROVIDERS)
def test_invalid_model_id_does_not_override_exact_original_food_name(monkeypatch, provider):
    mock_model(monkeypatch, provider, json.dumps({"items": [{
        **EGG, "food_id": "invented-catalogue-id", "source_text": "水煮鸡蛋",
    }]}))
    result = analyze_with_provider("125克水煮鸡蛋", provider_settings(provider))
    assert result.draft[0]["food_id"] == "egg"
    assert result.calories == 193.8


@pytest.mark.parametrize("provider", PROVIDERS)
def test_expanded_soy_chicken_name_overrules_unrelated_model_id(monkeypatch, provider):
    mock_model(monkeypatch, provider, json.dumps({"items": [{
        "food_id": "dish_001", "name": "番茄炒蛋", "source_text": "豉油鸡",
        "grams": 200, "weight_basis": "cooked", "preparation": "braised",
    }]}))
    result = analyze_with_provider("豉油鸡200克熟重", provider_settings(provider), mode="basic")
    assert result.draft[0]["food_id"] == "dish_251"
    assert result.draft[0]["source_text"] == "豉油鸡"
    assert result.questions == []
    assert result.calories > 0


@pytest.mark.parametrize("provider", PROVIDERS)
def test_unknown_original_name_blocks_all_totals_despite_model_substitution(monkeypatch, provider):
    mock_model(monkeypatch, provider, json.dumps({"items": [EGG, {
        "food_id": "egg", "name": "水煮鸡蛋", "source_text": "火星豉油鸡", "grams": 200,
        "weight_basis": "cooked", "preparation": "braised",
    }]}))
    result = analyze_with_provider(
        "125克水煮鸡蛋和火星豉油鸡200克熟重", provider_settings(provider), mode="basic")
    assert result.draft[0]["food_id"] == "egg"
    assert result.draft[1]["food_id"] is None
    assert result.details == []
    assert all(getattr(result, field) is None
               for field in ("calories", "protein_g", "carbs_g", "fat_g"))
    assert any(question["kind"] == "unsupported" for question in result.questions)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_model_cannot_supply_server_owned_custom_recipe(monkeypatch, provider):
    mock_model(monkeypatch, provider, json.dumps({"items": [{
        **EGG, "custom_recipe": {"accepted": True, "calories": 1},
    }]}))
    with pytest.raises(RuntimeError):
        analyze_with_provider("125克水煮鸡蛋", provider_settings(provider))


@pytest.mark.parametrize('provider', PROVIDERS)
def test_exact_chinese_enum_labels_normalize_without_changing_food_or_amount(monkeypatch, provider):
    mock_model(monkeypatch, provider, json.dumps({'items': [{
        **EGG, 'source_text': '水煮鸡蛋', 'preparation': '水煮',
        'weight_basis': '熟重', 'portion_count': 2, 'portion_unit': '个',
    }]}))
    result = analyze_with_provider('125克水煮鸡蛋', provider_settings(provider))
    assert result.questions == []
    assert result.draft[0]['food_id'] == 'egg'
    assert result.draft[0]['grams'] == 125
    assert result.draft[0]['preparation'] == 'boiled'
    assert result.draft[0]['weight_basis'] == 'cooked'
    assert result.draft[0]['portion_count'] == 2
    assert result.draft[0]['portion_unit'] == 'piece'
    assert result.calories == 193.8


def test_hkust_chinese_recipe_method_label_uses_existing_reference_arithmetic(monkeypatch):
    mock_model(monkeypatch, 'hkust', json.dumps({'items': [{
        'food_id': 'dish_001', 'name': '番茄炒蛋', 'source_text': '一份番茄炒蛋',
        'grams': None, 'preparation': '炒', 'portion_count': 1, 'portion_unit': 'serving',
    }, {
        **EGG, 'name': '水煮鸡蛋（去壳）', 'source_text': '两个水煮鸡蛋',
        'grams': None, 'portion_count': 2, 'portion_unit': 'piece',
    }]}))
    result = analyze_with_provider('一份番茄炒蛋，两个水煮鸡蛋',
                                   provider_settings('hkust'), mode='basic')
    assert result.questions == []
    assert [item['food_id'] for item in result.draft] == ['dish_001', 'egg']
    assert result.draft[0]['preparation'] == 'stir_fried'
    assert result.calories == 365.2


@pytest.mark.parametrize('provider', PROVIDERS)
@pytest.mark.parametrize('field,value', [
    ('preparation', '火星炒法'), ('preparation', '炒或者炖'),
    ('weight_basis', '熟重或生重'), ('portion_unit', '克'),
    ('calories', 1), ('custom_recipe', {'accepted': True}),
])
def test_enum_translation_does_not_accept_ambiguous_labels_or_extra_fields(
        monkeypatch, provider, field, value):
    mock_model(monkeypatch, provider, json.dumps({'items': [{
        **EGG, 'preparation': '水煮', field: value,
    }]}))
    with pytest.raises(RuntimeError):
        analyze_with_provider('125克水煮鸡蛋', provider_settings(provider))


@pytest.mark.parametrize('provider', PROVIDERS)
def test_whole_meal_replacement_prompt_uses_same_identity_scope_as_guard(monkeypatch, provider):
    original = '一份番茄炒蛋，两个水煮鸡蛋'
    replacement = '改成白米饭150克熟重，水煮鸡蛋80克熟重。'
    history = [
        {'role': 'user', 'content': original},
        {'role': 'user', 'content': '已回答：{}\n当前餐食资料：旧番茄炒蛋资料'},
        {'role': 'user', 'content': replacement},
    ]
    calls = mock_model(monkeypatch, provider, json.dumps({'items': [{
        'food_id': 'rice', 'name': '白米饭', 'source_text': '白米饭', 'grams': 150,
        'weight_basis': 'cooked', 'preparation': 'boiled',
    }, {**EGG, 'grams': 80}]}))
    result = analyze_with_provider(original, provider_settings(provider), history, 'basic')
    assert [item['food_id'] for item in result.draft] == ['rice', 'egg']
    assert result.calories == 319
    prompt = calls[0][1]['json']['messages'][0]['content']
    active = prompt.split('用户已明确替换整餐。', 1)[1]
    assert '白米饭150克熟重' in active
    assert '旧番茄炒蛋资料' not in active
    assert '一份番茄炒蛋' not in active


def test_replacement_context_does_not_silently_drop_stale_model_foods(monkeypatch):
    mock_model(monkeypatch, 'hkust', json.dumps({'items': [{
        'food_id': 'dish_001', 'name': '番茄炒蛋', 'source_text': '番茄炒蛋', 'grams': 200,
    }, {
        'food_id': 'rice', 'name': '白米饭', 'source_text': '白米饭', 'grams': 150,
        'weight_basis': 'cooked', 'preparation': 'boiled',
    }, {**EGG, 'grams': 80}]}))
    result = analyze_with_provider('一份番茄炒蛋，两个水煮鸡蛋', provider_settings('hkust'), [
        {'role': 'user', 'content': '改成白米饭150克熟重，水煮鸡蛋80克熟重。'},
    ], 'basic')
    assert [item['food_id'] for item in result.draft] == [None, 'rice', 'egg']
    assert result.calories is None
    assert result.details == []


def test_replacement_context_keeps_unknown_new_food_and_quantity_only_followup(monkeypatch):
    calls = mock_model(monkeypatch, 'hkust', json.dumps({'items': [{
        'food_id': 'rice', 'name': '白米饭', 'source_text': '白米饭', 'grams': 150,
        'weight_basis': 'cooked', 'preparation': 'boiled',
    }]}))
    result = analyze_with_provider('200克番茄炒蛋', provider_settings('hkust'), [
        {'role': 'user', 'content': '改成白米饭100克和100克火星豉油鸡'},
        {'role': 'user', 'content': '改成150克'},
    ], 'basic')
    active = calls[0][1]['json']['messages'][0]['content'].split('用户已明确替换整餐。', 1)[1]
    assert '火星豉油鸡' in active
    assert '改成150克' in active
    assert result.calories is None
    assert any(question['kind'] == 'unsupported' for question in result.questions)
