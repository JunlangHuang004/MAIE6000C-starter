from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    food_text: str = Field(min_length=3, max_length=2000)

    @field_validator("food_text", mode="before")
    @classmethod
    def strip_food_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class AnalysisRead(BaseModel):
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
    analysis_id: str
    food_text: str = Field(min_length=3, max_length=2000)


class NutritionAnalysisResponse(BaseModel):
    calories: float = Field(ge=0.0)
    protein_g: float = Field(ge=0.0)
    carbs_g: float = Field(ge=0.0)
    fat_g: float = Field(ge=0.0)
