from __future__ import annotations

import logging
import time

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.common.config import configure_logging, get_settings
from services.common.db import get_session_factory
from services.common.models import (
    Analysis,
    AnalysisStatus,
    Case,
    CaseStatus,
    Job,
    JobStatus,
    JobType,
    utcnow,
)
from services.common.schemas import NutritionAnalysisResponse, TriageResponse

configure_logging()
logger = logging.getLogger("services.worker.main")
settings = get_settings()


def claim_next_pending_job(db: Session) -> Job | None:
    stmt = (
        select(Job)
        .where(Job.status == JobStatus.PENDING.value)
        .order_by(Job.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = db.execute(stmt).scalars().first()
    if job is None:
        return None

    job.status = JobStatus.CLAIMED.value
    job.claimed_at = utcnow()
    job.attempts += 1
    db.commit()
    db.refresh(job)
    return job


def mark_job_failed(job_id: int, error_message: str) -> None:
    session_factory = get_session_factory()
    with session_factory() as db:
        job = db.get(Job, job_id)
        if job is None:
            return

        case = db.get(Case, job.case_id) if job.case_id else None
        job.status = JobStatus.FAILED.value
        job.error = error_message[:1000]
        job.completed_at = utcnow()

        if case is not None:
            case.status = CaseStatus.FAILED.value

        analysis = db.get(Analysis, job.analysis_id) if job.analysis_id else None
        if analysis is not None:
            analysis.status = AnalysisStatus.FAILED.value
            analysis.error_message = "估算服务暂时不可用，请重试或补充更清楚的餐食描述。"

        db.commit()


def process_triage_job(job_id: int) -> None:
    session_factory = get_session_factory()

    with session_factory() as db:
        job = db.get(Job, job_id)
        if job is None:
            return

        case = db.get(Case, job.case_id)
        if case is None:
            raise RuntimeError(f"Case not found for job {job_id}")

        payload = {
            "case_id": case.id,
            "title": case.title,
            "description": case.description,
        }

    response = httpx.post(
        f"{settings.ai_service_url}/triage",
        json=payload,
        timeout=settings.worker_request_timeout_seconds,
    )
    response.raise_for_status()
    triage = TriageResponse.model_validate(response.json())

    with session_factory() as db:
        job = db.get(Job, job_id)
        if job is None:
            return

        case = db.get(Case, job.case_id)
        if case is None:
            raise RuntimeError(f"Case not found while completing job {job_id}")

        case.status = CaseStatus.TRIAGED.value
        case.ai_label = triage.label
        case.ai_summary = triage.summary
        case.ai_confidence = triage.confidence

        job.status = JobStatus.COMPLETED.value
        job.error = None
        job.completed_at = utcnow()
        db.commit()

    logger.info("job_completed", extra={"job_id": job_id, "label": triage.label})


def process_nutrition_job(job_id: int) -> None:
    session_factory = get_session_factory()

    with session_factory() as db:
        job = db.get(Job, job_id)
        if job is None:
            return

        analysis = db.get(Analysis, job.analysis_id) if job.analysis_id else None
        if analysis is None:
            raise RuntimeError(f"Analysis not found for job {job_id}")

        payload = {
            "analysis_id": analysis.id,
            "food_text": analysis.food_text,
            "conversation": analysis.conversation, "draft": analysis.draft,
            "mode": analysis.mode,
        }

    response = httpx.post(
        f"{settings.ai_service_url}/analyze-nutrition",
        json=payload,
        timeout=settings.worker_request_timeout_seconds,
    )
    response.raise_for_status()
    nutrition = NutritionAnalysisResponse.model_validate(response.json())

    with session_factory() as db:
        job = db.get(Job, job_id)
        if job is None:
            return

        analysis = db.get(Analysis, job.analysis_id) if job.analysis_id else None
        if analysis is None:
            raise RuntimeError(f"Analysis not found while completing job {job_id}")

        analysis.status = "needs_input" if nutrition.questions else "completed"
        analysis.draft = nutrition.draft
        analysis.questions = nutrition.questions
        analysis.details = nutrition.details
        analysis.error_message = None
        if nutrition.questions:
            analysis.conversation = [*analysis.conversation, {
                "role": "assistant", "content": "\n".join(q['label'] for q in nutrition.questions)}]
        analysis.interpreted_food_text = nutrition.interpreted_food_text
        analysis.calories = nutrition.calories
        analysis.protein_g = nutrition.protein_g
        analysis.carbs_g = nutrition.carbs_g
        analysis.fat_g = nutrition.fat_g

        job.status = JobStatus.COMPLETED.value
        job.error = None
        job.completed_at = utcnow()
        db.commit()

    logger.info("job_completed", extra={"job_id": job_id, "analysis_id": payload["analysis_id"]})


def process_job(job_id: int) -> None:
    session_factory = get_session_factory()
    with session_factory() as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        job_type = job.job_type

    if job_type == JobType.TRIAGE_CASE.value:
        process_triage_job(job_id)
    elif job_type == JobType.ANALYZE_NUTRITION.value:
        process_nutrition_job(job_id)
    else:
        raise RuntimeError(f"Unsupported job type: {job_type}")


def run_worker() -> None:
    session_factory = get_session_factory()
    logger.info(
        "worker_started",
        extra={
            "poll_seconds": settings.worker_poll_seconds,
            "ai_service_url": settings.ai_service_url,
        },
    )

    while True:
        job = None
        try:
            with session_factory() as db:
                job = claim_next_pending_job(db)

            if job is None:
                time.sleep(settings.worker_poll_seconds)
                continue

            logger.info(
                "job_claimed",
                extra={
                    "job_id": job.id,
                    "case_id": job.case_id,
                    "analysis_id": job.analysis_id,
                },
            )
            process_job(job.id)

        except KeyboardInterrupt:
            logger.info("worker_stopped")
            raise

        except Exception as exc:
            logger.exception("job_processing_failed")
            if job is not None:
                mark_job_failed(job.id, str(exc))
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    run_worker()
