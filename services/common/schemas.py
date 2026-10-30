from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services.common.nutrition import parse_meal
from services.common.ingredient_recipe import IngredientRecipe
from services.common.models import AnalysisStatus, CaseStatus, JobStatus, JobType


class HealthResponse(BaseModel):
    service: str
    status: str


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
        if get_settings().nutrition_provider == "demo":
            parse_meal(value)
        return value


class AnalysisCorrection(AnalysisCreate):
    revision: int = Field(ge=1)


class AnalysisConfirm(BaseModel):
    revision: int = Field(ge=1)


class AnalysisMode(BaseModel):
    revision: int = Field(ge=1)
    mode: Literal["basic", "advanced"]


class AnalysisReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    message: str | None = Field(default=None, min_length=1, max_length=2000)
    answers: dict = Field(default_factory=dict, max_length=150)

    @model_validator(mode="after")
    def one_mode(self):
        if bool(self.message and self.message.strip()) == bool(self.answers):
            raise ValueError("请填写补充说明或回答问题，两者选一种。")
        return self


class AnalysisIngredientRecipe(IngredientRecipe):
    revision: int = Field(strict=True, ge=1)
    item_index: int = Field(strict=True, ge=0, le=29)


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
