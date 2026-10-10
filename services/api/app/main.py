from __future__ import annotations

import logging
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from services.common.config import configure_logging
from services.common.db import get_db
from services.common.models import (
    Analysis,
    AnalysisStatus,
    Case,
    CaseStatus,
    Job,
    JobStatus,
    JobType,
)
from services.common.schemas import (
    AnalysisCreate,
    AnalysisCreateResponse,
    AnalysisRead,
    CaseCreate,
    CaseCreateResponse,
    CaseRead,
    HealthResponse,
    JobRead,
)

configure_logging()
logger = logging.getLogger("services.api.main")

app = FastAPI(title="MAIE 6000C Starter API", version="0.1.0")

HTTP_REQUESTS = Counter(
    "api_http_requests_total",
    "Total API HTTP requests",
    ["method", "path", "status"],
)
HTTP_REQUEST_LATENCY = Histogram(
    "api_http_request_duration_seconds",
    "API request duration in seconds",
    ["method", "path"],
)
CASES_CREATED = Counter("api_cases_created_total", "Total cases created")
ANALYSES_CREATED = Counter("api_analyses_created_total", "Total analyses created")


def create_case_with_job(db: Session, payload: CaseCreate) -> tuple[Case, Job]:
    case = Case(
        title=payload.title.strip(),
        description=payload.description.strip(),
        status=CaseStatus.QUEUED.value,
    )
    db.add(case)
    db.flush()

    job = Job(
        case_id=case.id,
        job_type=JobType.TRIAGE_CASE.value,
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.commit()
    db.refresh(case)
    db.refresh(job)
    return case, job


def list_cases(db: Session, limit: int) -> list[Case]:
    stmt = select(Case).order_by(Case.created_at.desc()).limit(limit)
    return db.execute(stmt).scalars().all()


def get_case(db: Session, case_id: str) -> Case | None:
    return db.get(Case, case_id)


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def create_analysis_with_job(
    db: Session,
    payload: AnalysisCreate,
) -> tuple[Analysis, Job]:
    analysis = Analysis(
        food_text=payload.food_text.strip(),
        status=AnalysisStatus.QUEUED.value,
    )
    db.add(analysis)
    db.flush()

    job = Job(
        analysis_id=analysis.id,
        job_type=JobType.ANALYZE_NUTRITION.value,
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.commit()
    db.refresh(analysis)
    db.refresh(job)
    return analysis, job


def get_analysis(db: Session, analysis_id: str) -> Analysis | None:
    return db.get(Analysis, analysis_id)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    start = perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration = perf_counter() - start
        path = request.url.path
        status = str(response.status_code) if response is not None else "500"
        HTTP_REQUESTS.labels(request.method, path, status).inc()
        HTTP_REQUEST_LATENCY.labels(request.method, path).observe(duration)
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": path,
                "status_code": status,
                "duration_seconds": round(duration, 4),
            },
        )


@app.get("/", response_model=HealthResponse)
def root() -> HealthResponse:
    return HealthResponse(service="api", status="ok")


@app.get("/health/live", response_model=HealthResponse)
def health_live() -> HealthResponse:
    return HealthResponse(service="api", status="ok")


@app.get("/health/ready", response_model=HealthResponse)
def health_ready(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(service="api", status="ok")


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/cases", response_model=CaseCreateResponse, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)) -> CaseCreateResponse:
    case, job = create_case_with_job(db, payload)
    CASES_CREATED.inc()
    logger.info("case_created", extra={"case_id": case.id, "job_id": job.id})
    return CaseCreateResponse(
        case=CaseRead.model_validate(case),
        job=JobRead.model_validate(job),
    )


@app.get("/cases", response_model=list[CaseRead])
def read_cases(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[CaseRead]:
    return [CaseRead.model_validate(case) for case in list_cases(db, limit)]


@app.get("/cases/{case_id}", response_model=CaseRead)
def read_case(case_id: str, db: Session = Depends(get_db)) -> CaseRead:
    case = get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseRead.model_validate(case)


@app.get("/jobs/{job_id}", response_model=JobRead)
def read_job(job_id: int, db: Session = Depends(get_db)) -> JobRead:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead.model_validate(job)


@app.post("/analyses", response_model=AnalysisCreateResponse, status_code=201)
def create_analysis(
    payload: AnalysisCreate,
    db: Session = Depends(get_db),
) -> AnalysisCreateResponse:
    analysis, job = create_analysis_with_job(db, payload)
    ANALYSES_CREATED.inc()
    logger.info(
        "analysis_created",
        extra={"analysis_id": analysis.id, "job_id": job.id},
    )
    return AnalysisCreateResponse(
        analysis=AnalysisRead.model_validate(analysis),
        job=JobRead.model_validate(job),
    )


@app.get("/analyses/{analysis_id}", response_model=AnalysisRead)
def read_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
) -> AnalysisRead:
    analysis = get_analysis(db, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisRead.model_validate(analysis)
