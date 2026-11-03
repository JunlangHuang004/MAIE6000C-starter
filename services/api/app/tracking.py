"""Account-owned daily calorie and weight records and their 30-day history."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.api.app.auth import get_current_user
from services.common import tracking
from services.common.db import get_db
from services.common.models import Analysis, DailyRecord, User, utcnow
from services.common.schemas import (
    DailyRecordRead, DailyRecordUpdate, TrackingResponse,
)

router = APIRouter(tags=["tracking"])
_CONFLICT_MESSAGE = "This daily record has changed. Reload it before saving again."


def _date(value: str, *, earliest: date = tracking.MIN_RECORD_DATE) -> date:
    try:
        return tracking.parse_record_date(value, earliest=earliest)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def daily_records(
    db: Session, user_id: str, start: date, end: date,
) -> list[DailyRecordRead]:
    """Read each source once and join by day without persisting derived meal totals."""
    records = {
        record.record_date: record
        for record in db.scalars(select(DailyRecord).where(
            DailyRecord.user_id == user_id,
            DailyRecord.record_date.between(start, end),
        ))
    }
    meals = {
        consumed_on: (count, round(float(calories), 1))
        for consumed_on, count, calories in db.execute(
            select(Analysis.consumed_on, func.count(Analysis.id), func.sum(Analysis.calories))
            .where(
                Analysis.user_id == user_id,
                Analysis.status == "confirmed",
                Analysis.consumed_on.between(start, end),
                Analysis.calories.is_not(None),
            ).group_by(Analysis.consumed_on)
        )
    }
    days = []
    current = start
    while current <= end:
        record = records.get(current)
        meal_count, meal_calories = meals.get(current, (0, None))
        manual = record.manual_calories if record is not None else None
        calories = manual if manual is not None else meal_calories
        source = "manual" if manual is not None else "meals" if meal_count else None
        days.append(DailyRecordRead(
            date=current,
            revision=record.revision if record is not None else 0,
            weight_kg=record.weight_kg if record is not None else None,
            manual_calories=manual,
            meal_calories=meal_calories,
            meal_count=meal_count,
            calories=calories,
            calorie_source=source,
        ))
        current += timedelta(days=1)
    return days


@router.get("/daily-records/{record_date}", response_model=DailyRecordRead)
def read_daily_record(
    record_date: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DailyRecordRead:
    parsed = _date(record_date)
    return daily_records(db, user.id, parsed, parsed)[0]


@router.put("/daily-records/{record_date}", response_model=DailyRecordRead)
def save_daily_record(
    record_date: str,
    payload: DailyRecordUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DailyRecordRead:
    parsed = _date(record_date)
    values = payload.model_dump(exclude={"revision"})
    now = utcnow()
    if payload.revision == 0:
        db.add(DailyRecord(
            user_id=user.id, record_date=parsed, **values,
            revision=1, created_at=now, updated_at=now,
        ))
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=_CONFLICT_MESSAGE) from exc
    else:
        result = db.execute(
            update(DailyRecord).where(
                DailyRecord.user_id == user.id,
                DailyRecord.record_date == parsed,
                DailyRecord.revision == payload.revision,
            ).values(**values, revision=payload.revision + 1, updated_at=now),
            execution_options={"synchronize_session": False},
        )
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail=_CONFLICT_MESSAGE)
        db.commit()
    # Clear any identity-map copy after the conditional UPDATE.
    db.expire_all()
    return daily_records(db, user.id, parsed, parsed)[0]


@router.get("/tracking", response_model=TrackingResponse)
def read_tracking(
    end: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TrackingResponse:
    today = tracking.hong_kong_today()
    end_date = today if end is None else _date(end, earliest=tracking.MIN_TREND_END)
    start_date = end_date - timedelta(days=tracking.TREND_DAYS - 1)
    days = daily_records(db, user.id, start_date, end_date)
    return TrackingResponse(
        today=today, start_date=start_date, end_date=end_date, days=days,
        summary=tracking.summarize_days([day.model_dump() for day in days]),
    )
