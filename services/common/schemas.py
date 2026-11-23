from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from services.common.nutrition import parse_meal
from services.common.ingredient_recipe import IngredientRecipe
from services.common.models import AnalysisStatus, CaseStatus, JobStatus, JobType
from services.common.tracking import parse_record_date


class HealthResponse(BaseModel):
    service: str
    status: str


class AuthCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$")
    password: SecretStr = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_encoding(cls, value):
        try:
            value.get_secret_value().encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("Password must contain valid Unicode characters") from exc
        return value

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        if isinstance(value, str):
            if not value.isascii():
                raise ValueError("Username must use ASCII letters, digits or underscores")
            return value.strip().lower()
        return value


class UserRead(BaseModel):
    id: str
    username: str

    model_config = ConfigDict(from_attributes=True)


class ProfileFields(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    age_years: int = Field(ge=18, le=80)
    height_cm: float = Field(ge=120, le=220)
    weight_kg: float = Field(ge=30, le=250)
    sex: Literal["male", "female"]
    goal: Literal["gain_muscle", "lose_fat"]
    activity_level: Literal["sedentary", "light", "moderate", "high"]
    strength_training: bool | None = None
    reference_scope: Literal["general_adult", "professional_guidance"] | None = None


class ProfileUpdate(ProfileFields):
    revision: int = Field(ge=0, le=2_147_483_646)


class ProfileRead(ProfileFields):
    model_config = ConfigDict(from_attributes=True)

    revision: int = Field(ge=1)
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        # SQLite drops timezone metadata; persisted values are always written in UTC.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(
            timezone.utc,
        )


class ProfileResponse(BaseModel):
    profile: ProfileRead | None
    reference: dict[str, Any] | None


class IntakeCoverage(BaseModel):
    """User confirmation that each part of a day's intake was reviewed."""

    model_config = ConfigDict(extra="forbid", strict=True)

    breakfast: bool
    lunch: bool
    dinner: bool
    snacks: bool
    drinks: bool


class DailyRecordUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    revision: int = Field(ge=0, le=2_147_483_646)
    weight_kg: float | None = Field(ge=30, le=250)
    manual_calories: float | None = Field(ge=0, le=20000)
    exercise_calories: float | None = Field(default=None, ge=0, le=10000)
    intake_coverage: IntakeCoverage | None = None


class DailyRecordRead(BaseModel):
    date: date
    revision: int
    weight_kg: float | None
    manual_calories: float | None
    meal_calories: float | None
    meal_count: int
    calories: float | None
    calorie_source: Literal["manual", "meals"] | None
    exercise_calories: float | None
    baseline_expenditure_kcal: float | None
    total_expenditure_kcal: float | None
    balance_type: Literal["surplus", "deficit", "balanced"] | None
    balance_kcal: float | None
    intake_coverage: IntakeCoverage
    intake_complete: bool


class TrackingSummary(BaseModel):
    recorded_days: int
    average_calories: float | None
    weight_entries: int
    first_weight_kg: float | None
    last_weight_kg: float | None
    weight_change_kg: float | None


class TrackingResponse(BaseModel):
    timezone: Literal["Asia/Hong_Kong"] = "Asia/Hong_Kong"
    today: date
    start_date: date
    end_date: date
    days: list[DailyRecordRead]
    summary: TrackingSummary


class CaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=4000)


class CaseRead(BaseModel):
    id: str
    title: str
    description: str
    status: CaseStatus
    ai_label: str | None = None
    ai_summary: str | None = None
    ai_confidence: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobRead(BaseModel):
    id: int
    case_id: str | None = None
    analysis_id: str | None = None
    job_type: JobType
    status: JobStatus
    attempts: int
    error: str | None = None
    created_at: datetime
    claimed_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CaseCreateResponse(BaseModel):
    case: CaseRead
    job: JobRead


class AnalysisCreate(BaseModel):
    mode: Literal["basic", "advanced"] = "advanced"
    food_text: str = Field(min_length=1, max_length=2000)

    @field_validator("food_text", mode="before")
    @classmethod
    def strip_food_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("food_text")
    @classmethod
    def validate_supported_meal(cls, value):
        from services.common.config import get_settings
        if get_settings().effective_nutrition_provider == "demo":
            parse_meal(value)
        return value


class AnalysisCorrection(AnalysisCreate):
    revision: int = Field(ge=1, le=2_147_483_646, strict=True)


class AnalysisConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=1, le=2_147_483_646, strict=True)
    consumed_on: date | None = None

    @field_validator("consumed_on", mode="before")
    @classmethod
    def validate_consumed_on(cls, value):
        return None if value is None else parse_record_date(value)


class AnalysisMode(BaseModel):
    revision: int = Field(ge=1, le=2_147_483_646, strict=True)
    mode: Literal["basic", "advanced"]


class AnalysisReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1, le=2_147_483_646, strict=True)
    message: str | None = Field(default=None, min_length=1, max_length=2000)
    answers: dict = Field(default_factory=dict, max_length=150)

    @model_validator(mode="after")
    def one_mode(self):
        if bool(self.message and self.message.strip()) == bool(self.answers):
            raise ValueError("请填写补充说明或回答问题，两者选一种。")
        return self


class AnalysisIngredientRecipe(IngredientRecipe):
    revision: int = Field(strict=True, ge=1, le=2_147_483_646)
    item_index: int = Field(strict=True, ge=0, le=29)


ReferencePreparation = Literal[
    'raw', 'as_served', 'boiled', 'steamed', 'roasted', 'stir_fried', 'fried', 'braised', 'other',
]


class AnalysisReferenceCandidates(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    revision: int = Field(ge=1, le=2_147_483_646)
    item_index: int = Field(ge=0, le=29)
    ingredient_ids: list[str] = Field(default_factory=list, max_length=8)
    preparation: ReferencePreparation | None = None


class AnalysisReferenceInference(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    revision: int = Field(ge=1, le=2_147_483_646)
    item_index: int = Field(ge=0, le=29)


class AnalysisReferenceSelection(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    revision: int = Field(ge=1, le=2_147_483_646)
    item_index: int = Field(ge=0, le=29)
    offer_id: str = Field(min_length=16, max_length=100)
    food_id: str = Field(min_length=1, max_length=100)
    accepted: bool

    @model_validator(mode='after')
    def require_acknowledgment(self):
        if not self.accepted:
            raise ValueError('请先确认这只是近似参考，不是原食物的准确匹配。')
        return self


class RecipeRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    original_name: str = Field(min_length=1, max_length=120)
    ingredient_ids: list[str] = Field(min_length=1, max_length=8)
    preparation: ReferencePreparation


class RecipeInferenceRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    original_name: str = Field(min_length=1, max_length=120)


class RecipeRankCandidate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    food_id: str = Field(min_length=1, max_length=100)
    reason_zh: str = Field(min_length=1, max_length=240)
    reason_en: str = Field(min_length=1, max_length=400)
    differences_zh: list[str] = Field(min_length=1, max_length=5)
    differences_en: list[str] = Field(min_length=1, max_length=5)

    @field_validator('reason_zh', 'reason_en')
    @classmethod
    def plain_reason(cls, value):
        import re
        if (not value.strip() or re.search(r'[<>\x00-\x08\x0b-\x1f]', value)
                or re.search(r'\d\s*(?:kcal|calories?|kj|grams?|g\b|克|卡路里|千卡|千焦)'
                             r'|\b(?:energy|joules?|calories?|kcal|kilocalories?|kj|kilojoules?|protein|fat|'
                             r'carbohydrates?|carbs?|macros?|nutrition(?:al)?|nutrients?)\b'
                             r'|热量|能量|卡路里|千卡|千焦|蛋白质|脂肪|碳水|营养', value, re.I)):
            raise ValueError('Recommendation explanations must be plain text without nutrition')
        return value.strip()

    @field_validator('differences_zh', 'differences_en')
    @classmethod
    def plain_differences(cls, values):
        if any(len(value) > 400 for value in values):
            raise ValueError('Recommendation difference is too long')
        return [cls.plain_reason(value) for value in values]


class RecipeRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    provider: Literal['demo', 'qwen', 'hkust', 'ollama']
    candidates: list[RecipeRankCandidate] = Field(max_length=3)


class RecipeInferenceResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    provider: Literal['demo', 'qwen', 'hkust', 'ollama']
    status: Literal['suggested', 'needs_clarification']
    ingredient_ids: list[str] = Field(max_length=8)
    preparation: ReferencePreparation | None
    reason_zh: str = Field(min_length=1, max_length=240)
    reason_en: str = Field(min_length=1, max_length=400)

    @field_validator('reason_zh', 'reason_en')
    @classmethod
    def plain_reason(cls, value):
        import re
        value = RecipeRankCandidate.plain_reason(value)
        number = r'(?:\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百千万半]+)'
        measure = number + r'\s*(?:杯|份|勺)'
        # Match quantities, not isolated words or names such as 三杯鸡 and one-pot.
        if re.search(
                r'\b(?:\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten|'
                r'eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|'
                r'twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|'
                r'half|quarter|dozen)\s*(?:(?:of\s+)?an?\s+)?'
                r'(?:g|kg|mg|ml|l|oz|lb|grams?|kilograms?|milligrams?|'
                r'ounces?|pounds?|liters?|litres?|milliliters?|millilitres?|cups?|'
                r'tablespoons?|teaspoons?|servings?|portions?|percent(?:age)?)\b'
                + '|' + number + r'\s*(?:毫克|千克|公斤|克|毫升|升|斤|两|%|％)'
                + '|百分之' + number
                + '|' + measure + r'(?=$|[\s，。；、,.;])'
                + r'|(?:加入|添加|使用|取用|食用|吃|喝|用)\s*' + measure
                + r'|(?:confidence|similarity|score|相似度|置信度|可信度)\s*'
                r'(?:(?:is|of|为|是)\s*)?[:=：]?\s*' + number,
                value, re.I):
            raise ValueError('Inference explanations must not supply amounts or scores')
        return value

    @model_validator(mode='after')
    def coherent_inference(self):
        if self.status == 'suggested':
            if not self.ingredient_ids or self.preparation in (None, 'other'):
                raise ValueError('An inferred suggestion needs ingredients and a concrete method')
        elif self.ingredient_ids or self.preparation is not None:
            raise ValueError('Clarification must not retain unsubstantiated guesses')
        return self


class AnalysisRead(BaseModel):
    mode: Literal["basic", "advanced"] = "advanced"
    conversation: list = Field(default_factory=list)
    draft: list = Field(default_factory=list)
    questions: list = Field(default_factory=list)
    details: list = Field(default_factory=list)
    error_message: str | None = None
    interpreted_food_text: str | None = None
    revision: int
    confirmed_at: datetime | None = None
    consumed_on: date | None = None
    id: str
    food_text: str
    status: AnalysisStatus
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisCreateResponse(BaseModel):
    analysis: AnalysisRead
    job: JobRead


class TriageRequest(BaseModel):
    case_id: str
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=4000)


class TriageResponse(BaseModel):
    label: str = Field(min_length=1, max_length=50)
    summary: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


class NutritionAnalysisRequest(BaseModel):
    mode: Literal["basic", "advanced"] = "advanced"
    conversation: list[dict] = Field(default_factory=list, max_length=40)
    draft: list[dict] = Field(default_factory=list, max_length=30)
    analysis_id: str
    food_text: str = Field(min_length=1, max_length=2000)


class NutritionAnalysisResponse(BaseModel):
    draft: list[dict] = Field(default_factory=list, max_length=30)
    questions: list[dict] = Field(default_factory=list, max_length=150)
    details: list[dict] = Field(default_factory=list, max_length=30)
    interpreted_food_text: str | None = Field(default=None, max_length=10000)
    model_config = ConfigDict(allow_inf_nan=False)

    calories: float | None = Field(default=None, ge=0.0)
    protein_g: float | None = Field(default=None, ge=0.0)
    carbs_g: float | None = Field(default=None, ge=0.0)
    fat_g: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def complete_or_clarify(self):
        values = [self.calories, self.protein_g, self.carbs_g, self.fat_g]
        if self.questions:
            if any(v is not None for v in values) or not self.draft:
                raise ValueError("Pending questions cannot have totals")
        elif any(v is None for v in values):
            raise ValueError("A completed estimate needs every nutrient")
        return self
