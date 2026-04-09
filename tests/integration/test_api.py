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

def _make_instrument(file_type="RADAR_A", is_alert=False, diff=5.0, dept="wrs"):
    return InstrumentStatus(
        file_type=file_type,
        equipment_name=f"站台 {file_type}",
        ip="192.168.1.1",
        department=dept,
        latest_file_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        diff_time_minutes=diff,
        threshold_yellow=10.0,
        threshold_orange=15.0,
        threshold_red=20.0,
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

    def test_returns_503_when_db_error(self):
        with patch("backend.routers.completeness.get_all_instrument_statuses",
                   return_value=[]):
            res = client.get("/api/v1/completeness/current")
        assert res.status_code == 503

    def test_instrument_has_threshold_fields(self):
        instruments = [_make_instrument("RADAR_A")]
        with patch("backend.routers.completeness.get_all_instrument_statuses",
                   return_value=instruments):
            res = client.get("/api/v1/completeness/current")
        inst = res.json()["instruments"][0]
        assert "threshold_yellow" in inst
        assert "threshold_orange" in inst
        assert "threshold_red" in inst


# ── GET /api/v1/instruments ──────────────────────────────────

class TestGetInstruments:
    def test_returns_instrument_list(self):
        instruments = [
            {"file_type": "RADAR_A", "equipment_name": "站台 A",
             "threshold_yellow": 10.0, "threshold_orange": 15.0, "threshold_red": 20.0},
        ]
        with patch("backend.routers.instruments.list_instruments", return_value=instruments):
            res = client.get("/api/v1/instruments")
        assert res.status_code == 200
        data = res.json()
        assert len(data["instruments"]) == 1
        assert data["instruments"][0]["threshold_yellow"] == 10.0

    def test_returns_empty_list_on_db_error(self):
        with patch("backend.routers.instruments.list_instruments", return_value=[]):
            res = client.get("/api/v1/instruments")
        assert res.status_code == 200
        assert res.json()["instruments"] == []


# ── PUT /api/v1/instruments/{file_type}/threshold ───────────

class TestUpdateThreshold:
    def _instruments(self):
        return [{"file_type": "RADAR_A", "equipment_name": "站台 A",
                 "threshold_yellow": 10.0, "threshold_orange": 15.0, "threshold_red": 20.0}]

    def test_returns_200_on_valid_update(self):
        with patch("backend.routers.instruments.list_instruments", return_value=self._instruments()), \
             patch("backend.routers.instruments.set_instrument_thresholds") as mock_set:
            res = client.put(
                "/api/v1/instruments/RADAR_A/threshold",
                json={"threshold_yellow": 12.0, "threshold_orange": 18.0, "threshold_red": 25.0},
            )
        assert res.status_code == 200
        data = res.json()
        assert data["file_type"] == "RADAR_A"
        assert data["threshold_yellow"] == 12.0
        mock_set.assert_called_once_with("RADAR_A", 12.0, 18.0, 25.0)

    def test_returns_404_for_unknown_file_type(self):
        with patch("backend.routers.instruments.list_instruments", return_value=[]):
            res = client.put(
                "/api/v1/instruments/UNKNOWN/threshold",
                json={"threshold_yellow": 10.0, "threshold_orange": 15.0, "threshold_red": 20.0},
            )
        assert res.status_code == 404

    def test_returns_422_for_negative_threshold(self):
        res = client.put(
            "/api/v1/instruments/RADAR_A/threshold",
            json={"threshold_yellow": -1.0, "threshold_orange": 15.0, "threshold_red": 20.0},
        )
        assert res.status_code == 422

    def test_zero_threshold_is_valid(self):
        with patch("backend.routers.instruments.list_instruments", return_value=self._instruments()), \
             patch("backend.routers.instruments.set_instrument_thresholds"):
            res = client.put(
                "/api/v1/instruments/RADAR_A/threshold",
                json={"threshold_yellow": 0.0, "threshold_orange": 0.0, "threshold_red": 0.0},
            )
        assert res.status_code == 200


# ── GET /api/v1/system/current ──────────────────────────────

class TestSystemStatus:
    def test_returns_200(self):
        with patch("backend.routers.system.get_system_status", return_value=[
            {"ip": "192.168.1.1", "equipment_name": "Server A", "department": "wrs",
             "load_1": 0.5, "load_5": 0.4, "load_15": 0.3, "memory_use": 60.0}
        ]):
            res = client.get("/api/v1/system/current")
        assert res.status_code == 200
        assert len(res.json()["items"]) == 1


# ── GET /api/v1/disk/current ────────────────────────────────

class TestDiskStatus:
    def test_returns_200(self):
        with patch("backend.routers.system.get_disk_status", return_value=[
            {"ip": "192.168.1.1", "file_system": "/dev/sda1", "used_pct": 55.0,
             "equipment_name": "Server A", "department": "wrs"}
        ]):
            res = client.get("/api/v1/disk/current")
        assert res.status_code == 200
        assert len(res.json()["items"]) == 1
