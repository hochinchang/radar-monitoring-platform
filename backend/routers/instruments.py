"""
Instruments router — /api/v1/instruments/*
Manages per-instrument Max_DiffTime_Threshold settings.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from backend.models import (
    InstrumentListItem,
    InstrumentListResponse,
    InstrumentThresholdSetting,
    ThresholdUpdateResponse,
)
from backend.services.alert_service import (
    get_instrument_threshold,
    list_instruments,
    set_instrument_threshold,
)

logger = logging.getLogger("routers.instruments")
router = APIRouter(prefix="/api/v1/instruments", tags=["instruments"])


@router.get("", response_model=InstrumentListResponse)
def get_instruments() -> InstrumentListResponse:
    """Return all instruments with their current Max_DiffTime_Threshold."""
    items = list_instruments()
    return InstrumentListResponse(
        instruments=[
            InstrumentListItem(
                file_type=i["file_type"],
                equipment_name=i["equipment_name"],
                max_diff_time_threshold=i["max_diff_time_threshold"],
            )
            for i in items
        ]
    )


@router.put("/{file_type}/threshold", response_model=ThresholdUpdateResponse)
def update_threshold(
    file_type: str,
    body: InstrumentThresholdSetting,
) -> ThresholdUpdateResponse:
    """
    Update Max_DiffTime_Threshold for a specific instrument.
    Returns 404 if file_type is not found in FileTypeList.
    Returns 422 if threshold is negative (enforced by Pydantic Field ge=0).
    """
    # Verify the instrument exists
    instruments = list_instruments()
    known = {i["file_type"] for i in instruments}
    if file_type not in known:
        raise HTTPException(status_code=404, detail=f"找不到儀器: {file_type}")

    set_instrument_threshold(file_type, body.max_diff_time_threshold)
    logger.info("Threshold updated via API: %s -> %.1f", file_type, body.max_diff_time_threshold)

    return ThresholdUpdateResponse(
        file_type=file_type,
        max_diff_time_threshold=body.max_diff_time_threshold,
        updated_at=datetime.now(timezone.utc),
    )
