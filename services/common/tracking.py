"""Date boundaries and summaries for private daily records (no model inference)."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TRACKING_TIMEZONE = "Asia/Hong_Kong"
MIN_RECORD_DATE = date(2000, 1, 1)
TREND_DAYS = 30
MIN_TREND_END = MIN_RECORD_DATE + timedelta(days=TREND_DAYS - 1)


def hong_kong_today() -> date:
    return datetime.now(ZoneInfo(TRACKING_TIMEZONE)).date()


def parse_record_date(value: object, *, earliest: date = MIN_RECORD_DATE) -> date:
    """Accept an ISO calendar date, never a timestamp or numeric date coercion."""
    if type(value) is date:
        parsed = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Use a valid calendar date in YYYY-MM-DD format.") from exc
    else:
        raise ValueError("Use a valid calendar date in YYYY-MM-DD format.")
    if not earliest <= parsed <= hong_kong_today():
        raise ValueError(
            f"Date must be from {earliest.isoformat()} through today in Asia/Hong_Kong."
        )
    return parsed


def summarize_days(days: list[dict]) -> dict:
    """Missing values stay absent; a manually recorded zero is still a record."""
    calories = [day["calories"] for day in days if day["calories"] is not None]
    weights = [day["weight_kg"] for day in days if day["weight_kg"] is not None]
    return {
        "recorded_days": len(calories),
        "average_calories": round(sum(calories) / len(calories), 1) if calories else None,
        "weight_entries": len(weights),
        "first_weight_kg": weights[0] if weights else None,
        "last_weight_kg": weights[-1] if weights else None,
        "weight_change_kg": round(weights[-1] - weights[0], 2) if len(weights) >= 2 else None,
    }
