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
    ip: Optional[str] = None
    department: Optional[str] = None
    latest_file_time: Optional[datetime] = None
    diff_time_minutes: Optional[float] = None
    threshold_yellow: float  # 黃色警示閾值（分鐘）
    threshold_orange: float  # 橙色警示閾值（分鐘）
    threshold_red: float     # 紅色警示閾值（分鐘）
    is_alert: bool


class InstrumentThresholdSetting(BaseModel):
    threshold_yellow: float = Field(ge=0.0)
    threshold_orange: float = Field(ge=0.0)
    threshold_red: float = Field(ge=0.0)


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
