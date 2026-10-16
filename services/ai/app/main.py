from __future__ import annotations

import logging
from time import perf_counter

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from services.common.nutrition import estimate_meal
from services.common.meal_engine import evaluate_mode
from services.ai.app.qwen import analyze_with_qwen
from services.common.config import configure_logging, get_settings
from services.common.schemas import (
    HealthResponse,
    NutritionAnalysisRequest,
    NutritionAnalysisResponse,
    TriageRequest,
    TriageResponse,
)

configure_logging()
logger = logging.getLogger("services.ai.main")

app = FastAPI(title="MAIE 6000C Starter AI Service", version="0.1.0")

TRIAGE_REQUESTS = Counter("ai_triage_requests_total", "Total triage requests", ["label"])
TRIAGE_LATENCY = Histogram("ai_triage_duration_seconds", "Triage duration in seconds")
NUTRITION_REQUESTS = Counter(
    "ai_nutrition_analysis_requests_total",
    "Total nutrition analysis requests",
)
NUTRITION_LATENCY = Histogram(
    "ai_nutrition_analysis_duration_seconds",
    "Nutrition analysis duration in seconds",
)

LABEL_KEYWORDS = {
    "incident": {"error", "outage", "down", "failed", "failure", "broken", "crash", "bug"},
    "access": {"login", "password", "access", "permission", "unlock", "sign in", "signin"},
    "billing": {"invoice", "charge", "refund", "billing", "payment", "subscription"},
    "maintenance": {"upgrade", "patch", "maintenance", "deploy", "deployment", "scheduled"},
}



def shorten(text: str, max_words: int = 24) -> str:
    words = text.split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + "..."


def triage_text(title: str, description: str) -> TriageResponse:
    text = f"{title} {description}".lower()
    scores = {
        label: sum(1 for keyword in keywords if keyword in text)
        for label, keywords in LABEL_KEYWORDS.items()
    }

    label, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        label = "general"
        confidence = 0.45
    else:
        confidence = min(0.55 + 0.08 * score, 0.95)

    summary = shorten(f"{title.strip()}: {description.strip()}")
    return TriageResponse(label=label, summary=summary, confidence=round(confidence, 2))


def analyze_nutrition_text(food_text: str) -> NutritionAnalysisResponse:
    return NutritionAnalysisResponse(
        **estimate_meal(food_text), interpreted_food_text=food_text,
    )


@app.get("/", response_model=HealthResponse)
def root() -> HealthResponse:
    return HealthResponse(service="ai", status="ok")


@app.get("/health/live", response_model=HealthResponse)
def health_live() -> HealthResponse:
    return HealthResponse(service="ai", status="ok")


@app.get("/health/ready", response_model=HealthResponse)
def health_ready() -> HealthResponse:
    return HealthResponse(service="ai", status="ok")


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/triage", response_model=TriageResponse)
def triage(payload: TriageRequest) -> TriageResponse:
    start = perf_counter()
    result = triage_text(payload.title, payload.description)
    TRIAGE_REQUESTS.labels(result.label).inc()
    TRIAGE_LATENCY.observe(perf_counter() - start)
    logger.info(
        "triage_completed",
        extra={
            "case_id": payload.case_id,
            "label": result.label,
            "confidence": result.confidence,
        },
    )
    return result


@app.post("/analyze-nutrition", response_model=NutritionAnalysisResponse)
def analyze_nutrition(payload: NutritionAnalysisRequest) -> NutritionAnalysisResponse:
    start = perf_counter()
    try:
        settings = get_settings()
        if payload.draft:
            result = NutritionAnalysisResponse(**evaluate_mode(payload.draft, payload.mode))
        elif settings.nutrition_provider == "qwen":
            result = analyze_with_qwen(
                payload.food_text, settings, payload.conversation, payload.mode)
        else:
            result = analyze_nutrition_text(payload.food_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    NUTRITION_REQUESTS.inc()
    NUTRITION_LATENCY.observe(perf_counter() - start)
    logger.info(
        "nutrition_analysis_completed",
        extra={"analysis_id": payload.analysis_id},
    )
    return result
