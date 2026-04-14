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
    interval_minutes: float          # 資料週期 T
    threshold_yellow: float          # T + 5（自動計算）
    threshold_orange: float          # T + 10（自動計算）
    threshold_red: float             # T + 20（自動計算）
    is_alert: bool


class InstrumentIntervalSetting(BaseModel):
    interval_minutes: float = Field(gt=0.0)  # 資料週期 T，必須大於 0


class CurrentStatusResponse(BaseModel):
    instruments: list[InstrumentStatus]
    calculated_at: datetime
    status: str


class InstrumentListItem(BaseModel):
    file_type: str
    equipment_name: str
    interval_minutes: float
    threshold_yellow: float
    threshold_orange: float
    threshold_red: float


class InstrumentListResponse(BaseModel):
    instruments: list[InstrumentListItem]


class ThresholdUpdateResponse(BaseModel):
    file_type: str
    interval_minutes: float
    threshold_yellow: float
    threshold_orange: float
    threshold_red: float
    updated_at: datetime
