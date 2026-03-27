"""
Pydantic data models for radar-monitoring-platform.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- Core domain models ---

class CompletenessResult(BaseModel):
    completeness_rate: float  # 0.0 ~ 100.0
    calculated_at: datetime
    status: Literal["ok", "no_data", "db_error"]


class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    completeness_rate: float
    is_alert: bool


class InstrumentStatus(BaseModel):
    file_type: str
    equipment_name: str
    department: Optional[str] = None
    latest_file_time: Optional[datetime] = None
    diff_time_minutes: Optional[float] = None
    max_diff_time_threshold: float
    is_alert: bool


class InstrumentThresholdSetting(BaseModel):
    max_diff_time_threshold: float = Field(ge=0.0)


# --- API response wrappers ---

class CurrentStatusResponse(BaseModel):
    instruments: list[InstrumentStatus]
    calculated_at: datetime
    status: str


class TimeSeriesResponse(BaseModel):
    data: list[TimeSeriesPoint]
    start: datetime
    end: datetime


class InstrumentListItem(BaseModel):
    file_type: str
    equipment_name: str
    max_diff_time_threshold: float


class InstrumentListResponse(BaseModel):
    instruments: list[InstrumentListItem]


class ThresholdUpdateResponse(BaseModel):
    file_type: str
    max_diff_time_threshold: float
    updated_at: datetime
