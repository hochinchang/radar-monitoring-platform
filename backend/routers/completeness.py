"""
Completeness router — /api/v1/completeness/*
Thin layer: validates input, delegates to services.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from backend.models import CurrentStatusResponse, TimeSeriesResponse
from backend.services.alert_service import get_all_instrument_statuses
from backend.services.completeness_service import get_time_series

logger = logging.getLogger("routers.completeness")
router = APIRouter(prefix="/api/v1/completeness", tags=["completeness"])


@router.get("/current", response_model=CurrentStatusResponse)
def get_current_status() -> CurrentStatusResponse:
    """
    Return the latest alert status for all instruments.
    Based on radarFileCheck snapshot — reflects current state.
    Returns 503 if no instruments could be retrieved (DB error).
    """
    instruments = get_all_instrument_statuses()

    if not instruments:
        raise HTTPException(
            status_code=503,
            detail={"status": "db_error", "message": "資料庫連線失敗或無儀器資料"},
        )

    return CurrentStatusResponse(
        instruments=instruments,
        calculated_at=datetime.now(timezone.utc),
        status="ok",
    )


@router.get("/timeseries", response_model=TimeSeriesResponse)
def get_timeseries(
    start: datetime | None = Query(default=None, description="查詢起始時間 (ISO 8601)"),
    end: datetime | None = Query(default=None, description="查詢結束時間 (ISO 8601)"),
) -> TimeSeriesResponse:
    """
    Return hourly aggregated completeness time series.
    Defaults to the last 24 hours if start/end are not provided.
    """
    now = datetime.now(timezone.utc)
    end_time = end or now
    start_time = start or (end_time - timedelta(hours=24))

    if start_time >= end_time:
        raise HTTPException(status_code=422, detail="start 必須早於 end")

    points = get_time_series(start_time, end_time)

    return TimeSeriesResponse(
        data=points,
        start=start_time,
        end=end_time,
    )
