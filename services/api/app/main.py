from __future__ import annotations

import logging
from time import perf_counter
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from services.common.config import configure_logging, get_settings
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
)
from services.common.schemas import (
    AnalysisMode,
    AnalysisIngredientRecipe,
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


@app.get("/app", include_in_schema=False)
def meal_app():
    return FileResponse(
        Path(__file__).parent / "static" / "index.html",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/app-assets/{filename}", include_in_schema=False)
def meal_app_asset(filename: str):
    if filename not in {"app.js", "i18n.js", "catalogue-en.js"}:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(
        Path(__file__).parent / "static" / filename,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/foods")
def supported_foods():
    from services.common.nutrition import NUTRITION_PER_100G
    from services.common.meal_engine import catalogue
    return {"provider": get_settings().nutrition_provider,
            "catalogue": catalogue(), "foods": list(NUTRITION_PER_100G),
            "unit": "grams", "max_grams": 10000,
            "source": "USDA SR Legacy CC0 + user-reviewed project reference recipes."}


def change_analysis(db, analysis_id, revision, allowed_states, values):
    if db.get(Analysis, analysis_id) is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    result = db.execute(
        update(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.revision == revision,
            Analysis.status.in_(allowed_states),
        ).values(**values, revision=Analysis.revision + 1, updated_at=utcnow())
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="State or revision changed; reload the estimate."
        )


@app.patch("/analyses/{analysis_id}", response_model=AnalysisCreateResponse)
def correct_analysis(
    analysis_id: str, payload: AnalysisCorrection, db: Session = Depends(get_db),
):
    change_analysis(db, analysis_id, payload.revision, ["completed", "failed", "needs_input"], {
        "food_text": payload.food_text, "status": "queued", "confirmed_at": None,
        "conversation": [{"role":"user", "content":payload.food_text}],
        "draft": [], "questions": [], "details": [], "error_message": None,
        "interpreted_food_text": None, "calories": None, "protein_g": None,
        "carbs_g": None, "fat_g": None,
    })
    job = Job(analysis_id=analysis_id, job_type=JobType.ANALYZE_NUTRITION.value,
              status=JobStatus.PENDING.value)
    db.add(job)
    db.commit()
    db.expire_all()
    return AnalysisCreateResponse(
        analysis=AnalysisRead.model_validate(db.get(Analysis, analysis_id)),
        job=JobRead.model_validate(job),
    )


@app.post("/analyses/{analysis_id}/confirm", response_model=AnalysisRead)
def confirm_analysis(
    analysis_id: str, payload: AnalysisConfirm, db: Session = Depends(get_db),
):
    change_analysis(db, analysis_id, payload.revision, ["completed"], {
        "status": "confirmed", "confirmed_at": utcnow(),
    })
    db.commit()
    db.expire_all()
    return AnalysisRead.model_validate(db.get(Analysis, analysis_id))


@app.post("/analyses/{analysis_id}/reply", response_model=AnalysisCreateResponse)
def reply_analysis(analysis_id: str, payload: AnalysisReply, db: Session = Depends(get_db)):
    import json
    from services.common.meal_engine import apply_answers, catalogue
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if (analysis.revision != payload.revision
            or analysis.status not in ("needs_input", "completed", "failed")):
        raise HTTPException(status_code=409, detail="记录已更新，请刷新后回答。")
    if payload.message and any('custom_recipe' in item for item in analysis.draft):
        raise HTTPException(status_code=422,
                            detail="本餐包含自定义食材配方，请使用配方编辑器修改，或开始新的一餐。")
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
    })
    job = Job(analysis_id=analysis_id, job_type=JobType.ANALYZE_NUTRITION.value,
              status=JobStatus.PENDING.value)
    db.add(job)
    db.commit()
    db.expire_all()
    return AnalysisCreateResponse(
        analysis=AnalysisRead.model_validate(db.get(Analysis, analysis_id)),
                                  job=JobRead.model_validate(job))


@app.post("/analyses/{analysis_id}/ingredients", response_model=AnalysisCreateResponse)
def replace_with_ingredient_recipe(
    analysis_id: str, payload: AnalysisIngredientRecipe, db: Session = Depends(get_db),
):
    from copy import deepcopy
    from services.common.ingredient_recipe import validate_ingredient_recipe
    from services.common.meal_engine import catalogue

    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if (analysis.revision != payload.revision
            or analysis.status not in ("needs_input", "completed", "failed")):
        raise HTTPException(status_code=409, detail="记录已更新，请刷新后回答。")
    if payload.item_index >= len(analysis.draft):
        raise HTTPException(status_code=422, detail="找不到要修改的食物，请刷新后重试。")
    if len(analysis.conversation or []) >= 36:
        raise HTTPException(status_code=422, detail="本次对话较长，请整理餐食描述后重新估算。")
    recipe_data = payload.model_dump(exclude={'revision', 'item_index'})
    try:
        recipe = validate_ingredient_recipe(
            recipe_data, {food['id']:food for food in catalogue()['foods']})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    draft = deepcopy(analysis.draft)
    original = draft[payload.item_index]
    original_name = original.get('original_name') or original['name']
    draft[payload.item_index] = {
        'food_id': None, 'name': recipe.name,
        'source_text': original.get('source_text') or original_name,
        'original_name': original_name, 'custom_recipe': recipe.model_dump(),
    }
    # The durable draft is the source of truth. Keep history concise and do not ask
    # a model to reinterpret the accepted ingredient quantities on this path.
    conversation = [*(analysis.conversation or []), {
        'role':'user', 'content':f'已确认自定义食材配方：{recipe.name}',
        'kind':'ingredient_recipe', 'item_index':payload.item_index,
    }]
    change_analysis(db, analysis_id, payload.revision, ["needs_input", "completed", "failed"], {
        "conversation":conversation, "draft":draft, "questions":[], "details":[],
        "status":"queued", "confirmed_at":None, "error_message":None,
        "interpreted_food_text":None, "calories":None, "protein_g":None,
        "carbs_g":None, "fat_g":None,
    })
    job = Job(analysis_id=analysis_id, job_type=JobType.ANALYZE_NUTRITION.value,
              status=JobStatus.PENDING.value)
    db.add(job)
    db.commit()
    db.expire_all()
    return AnalysisCreateResponse(
        analysis=AnalysisRead.model_validate(db.get(Analysis, analysis_id)),
        job=JobRead.model_validate(job),
    )


@app.post("/analyses/{analysis_id}/mode", response_model=AnalysisCreateResponse)
def switch_analysis_mode(analysis_id: str, payload: AnalysisMode, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    # Reuse explicit facts only. Basic-mode defaults are never written into this draft.
    change_analysis(db, analysis_id, payload.revision, ["needs_input", "completed", "failed"], {
        "mode":payload.mode, "status":"queued", "questions":[], "details":[],
        "calories":None, "protein_g":None, "carbs_g":None, "fat_g":None,
        "interpreted_food_text":None, "error_message":None,
    })
    job = Job(analysis_id=analysis_id, job_type=JobType.ANALYZE_NUTRITION.value,
              status=JobStatus.PENDING.value)
    db.add(job)
    db.commit()
    db.expire_all()
    return AnalysisCreateResponse(
        analysis=AnalysisRead.model_validate(db.get(Analysis, analysis_id)),
        job=JobRead.model_validate(job))
