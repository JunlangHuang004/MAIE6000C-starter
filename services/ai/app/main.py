from __future__ import annotations

import logging
import re
from time import perf_counter

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from services.common.config import configure_logging
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

# Approximate nutrition per 100 g. This small, deterministic catalogue keeps the
# Week 7 vertical slice testable; it can later be replaced by an AI model or food API.
NUTRITION_PER_100G = {
    "chicken breast": (165.0, 31.0, 0.0, 3.6),
    "white rice": (130.0, 2.7, 28.0, 0.3),
    "rice": (130.0, 2.7, 28.0, 0.3),
    "egg": (155.0, 13.0, 1.1, 11.0),
    "salmon": (208.0, 20.0, 0.0, 13.0),
    "broccoli": (35.0, 2.4, 7.2, 0.4),
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
    text = food_text.lower()
    totals = [0.0, 0.0, 0.0, 0.0]

    for food_name, nutrients in NUTRITION_PER_100G.items():
        match = re.search(
            rf"(\d+(?:\.\d+)?)\s*g\s+(?:cooked\s+)?{re.escape(food_name)}\b",
            text,
        )
        if match is None:
            continue
        factor = float(match.group(1)) / 100.0
        totals = [total + nutrient * factor for total, nutrient in zip(totals, nutrients)]

    # Unknown free text still receives a conservative demo estimate so the async
    # workflow completes. A production version should return uncertainty/source data.
    if totals == [0.0, 0.0, 0.0, 0.0]:
        totals = [200.0, 10.0, 25.0, 7.0]

    return NutritionAnalysisResponse(
        calories=round(totals[0], 1),
        protein_g=round(totals[1], 1),
        carbs_g=round(totals[2], 1),
        fat_g=round(totals[3], 1),
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
    result = analyze_nutrition_text(payload.food_text)
    NUTRITION_REQUESTS.inc()
    NUTRITION_LATENCY.observe(perf_counter() - start)
    logger.info(
        "nutrition_analysis_completed",
        extra={"analysis_id": payload.analysis_id},
    )
    return result
