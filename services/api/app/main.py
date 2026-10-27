from __future__ import annotations

import logging
from time import perf_counter
from pathlib import Path

from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from sqlalchemy import and_, or_, select, text, update
from sqlalchemy.orm import Session

from services.common.config import configure_logging, get_settings
from services.api.app.auth import get_current_user, get_optional_user, router as auth_router
from services.common.db import get_db
from services.common.models import (
    Analysis,
    AnalysisStatus,
    utcnow,
    Case,
    CaseStatus,
    Job,
    JobStatus,
    JobType,
    User,
)
from services.common.schemas import (
    AnalysisMode,
    AnalysisReply,
    AnalysisConfirm,
    AnalysisCorrection,
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

app = FastAPI(title="NutriChat API", version="0.1.0")
app.include_router(auth_router)

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


def create_case_with_job(
    db: Session, payload: CaseCreate, user_id: str | None = None,
) -> tuple[Case, Job]:
    case = Case(
        user_id=user_id,
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


def list_cases(db: Session, limit: int, user_id: str | None = None) -> list[Case]:
    stmt = select(Case)
    if user_id is not None:
        stmt = stmt.where(Case.user_id == user_id)
    stmt = stmt.order_by(Case.created_at.desc(), Case.id.desc()).limit(limit)
    return db.execute(stmt).scalars().all()


def get_case(db: Session, case_id: str, user_id: str | None = None) -> Case | None:
    stmt = select(Case).where(Case.id == case_id)
    if user_id is not None:
        stmt = stmt.where(Case.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_job(db: Session, job_id: int, user_id: str | None = None) -> Job | None:
    stmt = select(Job).where(Job.id == job_id)
    if user_id is not None:
        stmt = stmt.where(or_(
            and_(Job.case_id.is_(None), Job.analysis.has(Analysis.user_id == user_id)),
            and_(Job.analysis_id.is_(None), Job.case.has(Case.user_id == user_id)),
        ))
    return db.execute(stmt).scalar_one_or_none()


def create_analysis_with_job(
    db: Session,
    payload: AnalysisCreate,
    user_id: str | None = None,
) -> tuple[Analysis, Job]:
    analysis = Analysis(
        user_id=user_id,
        food_text=payload.food_text.strip(),
        conversation=[{"role":"user", "content":payload.food_text.strip()}],
        mode=payload.mode,
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


def get_analysis(db: Session, analysis_id: str, user_id: str | None = None) -> Analysis | None:
    stmt = select(Analysis).where(Analysis.id == analysis_id)
    if user_id is not None:
        stmt = stmt.where(Analysis.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


@app.exception_handler(RequestValidationError)
async def safe_validation_errors(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/auth/"):
        # FastAPI's default validation response can echo the rejected password.
        return JSONResponse(status_code=422, content={
            "detail": "Use a 3–32 character username (letters, digits or _) and a "
                      "10–128 character password.",
        })
    return await request_validation_exception_handler(request, exc)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    start = perf_counter()
    response: Response | None = None
    try:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and (
            request.headers.get("X-NutriChat-Request") != "1"
            or ("origin" in request.headers
                and request.headers["origin"] != get_settings().auth_public_origin)
        ):
            response = JSONResponse(status_code=403, content={
                "detail": "Request origin or security header is invalid.",
            })
        else:
            response = await call_next(request)
        if request.url.path.startswith(("/auth/", "/analyses", "/cases", "/jobs")) or (
            request.url.path in {"/app", "/login"}
        ):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    finally:
        duration = perf_counter() - start
        route = request.scope.get("route")
        path = route.path if route is not None else "unmatched"
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
def create_case(
    payload: CaseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user),
) -> CaseCreateResponse:
    case, job = create_case_with_job(db, payload, user.id)
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
    user: User = Depends(get_current_user),
) -> list[CaseRead]:
    return [CaseRead.model_validate(case) for case in list_cases(db, limit, user.id)]


@app.get("/cases/{case_id}", response_model=CaseRead)
def read_case(
    case_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user),
) -> CaseRead:
    case = get_case(db, case_id, user.id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseRead.model_validate(case)


@app.get("/jobs/{job_id}", response_model=JobRead)
def read_job(
    job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user),
) -> JobRead:
    job = get_job(db, job_id, user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead.model_validate(job)


@app.post("/analyses", response_model=AnalysisCreateResponse, status_code=201)
def create_analysis(
    payload: AnalysisCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisCreateResponse:
    analysis, job = create_analysis_with_job(db, payload, user.id)
    ANALYSES_CREATED.inc()
    logger.info(
        "analysis_created",
        extra={"analysis_id": analysis.id, "job_id": job.id},
    )
    return AnalysisCreateResponse(
        analysis=AnalysisRead.model_validate(analysis),
        job=JobRead.model_validate(job),
    )


@app.get("/analyses", response_model=list[AnalysisRead])
def read_analyses(
    limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AnalysisRead]:
    records = db.execute(select(Analysis).where(Analysis.user_id == user.id).order_by(
        Analysis.created_at.desc(), Analysis.id.desc(),
    ).limit(limit)).scalars().all()
    return [AnalysisRead.model_validate(record) for record in records]


@app.get("/analyses/{analysis_id}", response_model=AnalysisRead)
def read_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisRead:
    analysis = get_analysis(db, analysis_id, user.id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisRead.model_validate(analysis)


@app.get("/app", include_in_schema=False)
def meal_app(user: User | None = Depends(get_optional_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/login", include_in_schema=False)
def account_app():
    return FileResponse(Path(__file__).parent / "static" / "account.html")


@app.get("/foods")
def supported_foods():
    from services.common.nutrition import NUTRITION_PER_100G
    from services.common.meal_engine import catalogue
    return {"provider": get_settings().nutrition_provider,
            "catalogue": catalogue(), "foods": list(NUTRITION_PER_100G),
            "unit": "grams", "max_grams": 10000,
            "source": "USDA SR Legacy CC0 + user-reviewed project reference recipes."}


def change_analysis(db, analysis_id, revision, allowed_states, values, user_id=None):
    if get_analysis(db, analysis_id, user_id) is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    predicates = [
        Analysis.id == analysis_id,
        Analysis.revision == revision,
        Analysis.status.in_(allowed_states),
    ]
    if user_id is not None:
        predicates.append(Analysis.user_id == user_id)
    result = db.execute(
        update(Analysis).where(*predicates).values(
            **values, revision=Analysis.revision + 1, updated_at=utcnow(),
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="State or revision changed; reload the estimate."
        )


@app.patch("/analyses/{analysis_id}", response_model=AnalysisCreateResponse)
def correct_analysis(
    analysis_id: str, payload: AnalysisCorrection, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    change_analysis(db, analysis_id, payload.revision, ["completed", "failed", "needs_input"], {
        "food_text": payload.food_text, "status": "queued", "confirmed_at": None,
        "conversation": [{"role":"user", "content":payload.food_text}],
        "draft": [], "questions": [], "details": [], "error_message": None,
        "interpreted_food_text": None, "calories": None, "protein_g": None,
        "carbs_g": None, "fat_g": None,
    }, user_id=user.id)
    job = Job(analysis_id=analysis_id, job_type=JobType.ANALYZE_NUTRITION.value,
              status=JobStatus.PENDING.value)
    db.add(job)
    db.commit()
    db.expire_all()
    return AnalysisCreateResponse(
        analysis=AnalysisRead.model_validate(get_analysis(db, analysis_id, user.id)),
        job=JobRead.model_validate(job),
    )


@app.post("/analyses/{analysis_id}/confirm", response_model=AnalysisRead)
def confirm_analysis(
    analysis_id: str, payload: AnalysisConfirm, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    change_analysis(db, analysis_id, payload.revision, ["completed"], {
        "status": "confirmed", "confirmed_at": utcnow(),
    }, user_id=user.id)
    db.commit()
    db.expire_all()
    return AnalysisRead.model_validate(get_analysis(db, analysis_id, user.id))


@app.post("/analyses/{analysis_id}/reply", response_model=AnalysisCreateResponse)
def reply_analysis(
    analysis_id: str, payload: AnalysisReply, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    import json
    from services.common.meal_engine import apply_answers, catalogue
    analysis = get_analysis(db, analysis_id, user.id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if (analysis.revision != payload.revision
            or analysis.status not in ("needs_input", "completed", "failed")):
        raise HTTPException(status_code=409, detail="记录已更新，请刷新后回答。")
    if len(analysis.conversation) >= 36:
        raise HTTPException(status_code=422, detail="本次对话较长，请整理餐食描述后重新估算。")
    try:
        draft = (apply_answers(analysis.draft, payload.answers, analysis.mode)
                 if payload.answers else [])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if payload.answers:
        names = {f['id']: f['name'] for f in catalogue()['foods']}
        content = '已回答：'+json.dumps(payload.answers, ensure_ascii=False)
        # Include complete slot state for later natural-language corrections, but no nutrition.
        state = [{**item, 'catalogue_name':names.get(item.get('food_id'))} for item in draft]
        content += '\n当前餐食资料：'+json.dumps(state, ensure_ascii=False)
    else:
        content = payload.message.strip()
    conversation = analysis.conversation or [{"role":"user", "content":analysis.food_text}]
    display = payload.message.strip() if payload.message else '已补充：' + '；'.join(
        q['label'].split('？')[0] + ' → ' + (
            '已核对配方及成品重量' if q['kind'] == 'recipe' else
            '确认' if q['kind'] == 'confirm' else
            next((o['label'] for o in q.get('options', [])
                  if o['value'] == payload.answers[q['key']]), str(payload.answers[q['key']])))
        for q in analysis.questions if q['key'] in payload.answers)
    conversation = [*conversation, {"role":"user", "content":content, "display":display}]
    if len(json.dumps(conversation, ensure_ascii=False)) > 45000:
        raise HTTPException(status_code=422, detail="对话资料过长，请整理后开始新餐食。")
    change_analysis(db, analysis_id, payload.revision, ["needs_input", "completed", "failed"], {
        "conversation":conversation, "draft":draft, "questions":[], "details":[],
        "status":"queued", "confirmed_at":None, "error_message":None,
        "interpreted_food_text":None, "calories":None, "protein_g":None,
        "carbs_g":None, "fat_g":None,
    }, user_id=user.id)
    job = Job(analysis_id=analysis_id, job_type=JobType.ANALYZE_NUTRITION.value,
              status=JobStatus.PENDING.value)
    db.add(job)
    db.commit()
    db.expire_all()
    return AnalysisCreateResponse(
        analysis=AnalysisRead.model_validate(get_analysis(db, analysis_id, user.id)),
                                  job=JobRead.model_validate(job))


@app.post("/analyses/{analysis_id}/mode", response_model=AnalysisCreateResponse)
def switch_analysis_mode(
    analysis_id: str, payload: AnalysisMode, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    analysis = get_analysis(db, analysis_id, user.id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    # Reuse explicit facts only. Basic-mode defaults are never written into this draft.
    change_analysis(db, analysis_id, payload.revision, ["needs_input", "completed", "failed"], {
        "mode":payload.mode, "status":"queued", "questions":[], "details":[],
        "calories":None, "protein_g":None, "carbs_g":None, "fat_g":None,
        "interpreted_food_text":None, "error_message":None,
    }, user_id=user.id)
    job = Job(analysis_id=analysis_id, job_type=JobType.ANALYZE_NUTRITION.value,
              status=JobStatus.PENDING.value)
    db.add(job)
    db.commit()
    db.expire_all()
    return AnalysisCreateResponse(
        analysis=AnalysisRead.model_validate(get_analysis(db, analysis_id, user.id)),
        job=JobRead.model_validate(job))
