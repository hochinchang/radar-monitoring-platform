"""
API 整合測試 — 使用 httpx + FastAPI TestClient 測試各端點。
使用 pytest-mock 模擬 DB 連線失敗與服務層回應。
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import InstrumentStatus

client = TestClient(app)

# ── 共用 fixtures ────────────────────────────────────────────

def _make_instrument(file_type="RADAR_A", is_alert=False, diff=5.0):
    return InstrumentStatus(
        file_type=file_type,
        equipment_name=f"站台 {file_type}",
        latest_file_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        diff_time_minutes=diff,
        max_diff_time_threshold=30.0,
        is_alert=is_alert,
    )


# ── GET /api/v1/completeness/current ────────────────────────

class TestCurrentStatus:
    def test_returns_200_with_instruments(self):
        instruments = [_make_instrument("RADAR_A"), _make_instrument("RADAR_B")]
        with patch("backend.routers.completeness.get_all_instrument_statuses",
                   return_value=instruments):
            res = client.get("/api/v1/completeness/current")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert len(data["instruments"]) == 2
        assert data["instruments"][0]["file_type"] == "RADAR_A"

    def test_returns_503_when_db_error(self):
        with patch("backend.routers.completeness.get_all_instrument_statuses",
                   return_value=[]):
            res = client.get("/api/v1/completeness/current")
        assert res.status_code == 503

    def test_alert_instrument_has_is_alert_true(self):
        instruments = [_make_instrument("RADAR_A", is_alert=True, diff=45.0)]
        with patch("backend.routers.completeness.get_all_instrument_statuses",
                   return_value=instruments):
            res = client.get("/api/v1/completeness/current")
        assert res.status_code == 200
        assert res.json()["instruments"][0]["is_alert"] is True


# ── GET /api/v1/completeness/timeseries ─────────────────────

class TestTimeSeries:
    def test_returns_200_with_default_range(self):
        from backend.models import TimeSeriesPoint
        points = [
            TimeSeriesPoint(
                timestamp=datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc),
                completeness_rate=98.5,
                is_alert=False,
            )
        ]
        with patch("backend.routers.completeness.get_time_series", return_value=points):
            res = client.get("/api/v1/completeness/timeseries")
        assert res.status_code == 200
        data = res.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["completeness_rate"] == 98.5

    def test_returns_200_with_custom_range(self):
        with patch("backend.routers.completeness.get_time_series", return_value=[]):
            res = client.get(
                "/api/v1/completeness/timeseries"
                "?start=2024-01-14T00:00:00Z&end=2024-01-15T00:00:00Z"
            )
        assert res.status_code == 200
        assert res.json()["data"] == []

    def test_returns_422_when_start_after_end(self):
        res = client.get(
            "/api/v1/completeness/timeseries"
            "?start=2024-01-15T00:00:00Z&end=2024-01-14T00:00:00Z"
        )
        assert res.status_code == 422


# ── GET /api/v1/instruments ──────────────────────────────────

class TestGetInstruments:
    def test_returns_instrument_list(self):
        instruments = [
            {"file_type": "RADAR_A", "equipment_name": "站台 A", "max_diff_time_threshold": 30.0},
            {"file_type": "RADAR_B", "equipment_name": "站台 B", "max_diff_time_threshold": 60.0},
        ]
        with patch("backend.routers.instruments.list_instruments", return_value=instruments):
            res = client.get("/api/v1/instruments")
        assert res.status_code == 200
        data = res.json()
        assert len(data["instruments"]) == 2
        assert data["instruments"][0]["file_type"] == "RADAR_A"

    def test_returns_empty_list_on_db_error(self):
        with patch("backend.routers.instruments.list_instruments", return_value=[]):
            res = client.get("/api/v1/instruments")
        assert res.status_code == 200
        assert res.json()["instruments"] == []


# ── PUT /api/v1/instruments/{file_type}/threshold ───────────

class TestUpdateThreshold:
    def test_returns_200_on_valid_update(self):
        instruments = [
            {"file_type": "RADAR_A", "equipment_name": "站台 A", "max_diff_time_threshold": 30.0}
        ]
        with patch("backend.routers.instruments.list_instruments", return_value=instruments), \
             patch("backend.routers.instruments.set_instrument_threshold") as mock_set:
            res = client.put(
                "/api/v1/instruments/RADAR_A/threshold",
                json={"max_diff_time_threshold": 45.0},
            )
        assert res.status_code == 200
        data = res.json()
        assert data["file_type"] == "RADAR_A"
        assert data["max_diff_time_threshold"] == 45.0
        mock_set.assert_called_once_with("RADAR_A", 45.0)

    def test_returns_404_for_unknown_file_type(self):
        """需求 7.1 — 不存在的 file_type 回傳 404"""
        with patch("backend.routers.instruments.list_instruments", return_value=[]):
            res = client.put(
                "/api/v1/instruments/UNKNOWN/threshold",
                json={"max_diff_time_threshold": 30.0},
            )
        assert res.status_code == 404

    def test_returns_422_for_negative_threshold(self):
        """需求 7.5 — 負數閾值回傳 422"""
        res = client.put(
            "/api/v1/instruments/RADAR_A/threshold",
            json={"max_diff_time_threshold": -1.0},
        )
        assert res.status_code == 422

    def test_returns_422_for_zero_is_valid(self):
        """閾值 0 應被接受（ge=0）"""
        instruments = [
            {"file_type": "RADAR_A", "equipment_name": "站台 A", "max_diff_time_threshold": 30.0}
        ]
        with patch("backend.routers.instruments.list_instruments", return_value=instruments), \
             patch("backend.routers.instruments.set_instrument_threshold"):
            res = client.put(
                "/api/v1/instruments/RADAR_A/threshold",
                json={"max_diff_time_threshold": 0.0},
            )
        assert res.status_code == 200
