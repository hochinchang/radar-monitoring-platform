"""
Pydantic data models for radar-monitoring-platform.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InstrumentStatus(BaseModel):
    file_type: str
    equipment_name: str
    ip: Optional[str] = None
    department: Optional[str] = None
    latest_file_time: Optional[datetime] = None
    diff_time_minutes: Optional[float] = None
    threshold_yellow: float
    threshold_orange: float
    threshold_red: float
    is_alert: bool


class InstrumentThresholdSetting(BaseModel):
    threshold_yellow: float = Field(ge=0.0)
    threshold_orange: float = Field(ge=0.0)
    threshold_red: float = Field(ge=0.0)


class CurrentStatusResponse(BaseModel):
    instruments: list[InstrumentStatus]
    calculated_at: datetime
    status: str


class InstrumentListItem(BaseModel):
    file_type: str
    equipment_name: str
    threshold_yellow: float
    threshold_orange: float
    threshold_red: float


class InstrumentListResponse(BaseModel):
    instruments: list[InstrumentListItem]


class ThresholdUpdateResponse(BaseModel):
    file_type: str
    threshold_yellow: float
    threshold_orange: float
    threshold_red: float
    updated_at: datetime
