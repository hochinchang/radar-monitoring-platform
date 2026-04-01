"""
Alert service for radar-monitoring-platform.
Queries all FileCheck tables for each instrument's latest snapshot,
calculates diff_time_minutes, and compares against per-instrument thresholds.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from backend.config import get_config
from backend.database import get_session
from backend.models import InstrumentStatus

logger = logging.getLogger("alert_service")

# Runtime threshold store: file_type -> (yellow, orange, red)
_thresholds: dict[str, Tuple[float, float, float]] = {}

_INSTRUMENT_STATUS_SQL = text("""
SELECT
    ftl.FileType,
    ftl.EquipmentName,
    fc.IP,
    fc.FileTime,
    TIMESTAMPDIFF(SECOND, FROM_UNIXTIME(fc.FileTime), NOW()) / 60.0 AS diff_time_minutes
FROM FileTypeList ftl
LEFT JOIN (
    SELECT IP, FileType, FileTime FROM radarFileCheck
    UNION ALL
    SELECT IP, FileType, FileTime FROM HFradarFileCheck
    UNION ALL
    SELECT IP, FileType, FileTime FROM satelliteFileCheck
    UNION ALL
    SELECT IP, FileType, FileTime FROM windprofilerFileCheck
    UNION ALL
    SELECT IP, FileType, FileTime FROM DSFileCheck
) fc ON ftl.FileType = fc.FileType
""")

_SYSTEM_IP_DEPT_SQL = text("SELECT IP, Department FROM SystemIPList")


def _default_thresholds() -> Tuple[float, float, float]:
    s = get_config().system
    return (s.default_threshold_yellow, s.default_threshold_orange, s.default_threshold_red)


def _get_thresholds() -> dict[str, Tuple[float, float, float]]:
    if not _thresholds:
        cfg = get_config()
        for file_type, inst_cfg in cfg.instruments.items():
            _thresholds[file_type] = (inst_cfg.threshold_yellow, inst_cfg.threshold_orange, inst_cfg.threshold_red)
        logger.info("Thresholds initialised: %d instruments", len(_thresholds))
    return _thresholds


def _load_ip_department_map() -> dict[str, str]:
    try:
        with get_session("system_status") as session:
            rows = session.execute(_SYSTEM_IP_DEPT_SQL).fetchall()
        return {row.IP: (row.Department or "") for row in rows}
    except Exception as exc:
        logger.warning("Failed to load IP->Department map: %s", exc)
        return {}


def get_all_instrument_statuses() -> list[InstrumentStatus]:
    thresholds = _get_thresholds()
    default = _default_thresholds()
    timeout = get_config().system.query_timeout_seconds
    ip_dept = _load_ip_department_map()

    try:
        with get_session("file_status") as session:
            rows = session.execute(
                _INSTRUMENT_STATUS_SQL.execution_options(timeout=timeout)
            ).fetchall()
    except (OperationalError, SQLAlchemyError) as exc:
        logger.error("get_all_instrument_statuses: DB error: %s", exc)
        return []

    statuses: list[InstrumentStatus] = []
    for row in rows:
        file_type: str = row.FileType
        t_yellow, t_orange, t_red = thresholds.get(file_type, default)
        department = ip_dept.get(row.IP or "", "") or None

        # 找不到對應科別的儀器不顯示
        if not department:
            continue

        if row.FileTime is None or row.diff_time_minutes is None:
            statuses.append(InstrumentStatus(
                file_type=file_type,
                equipment_name=row.EquipmentName or "",
                ip=row.IP or None,
                department=department,
                latest_file_time=None,
                diff_time_minutes=None,
                threshold_yellow=t_yellow,
                threshold_orange=t_orange,
                threshold_red=t_red,
                is_alert=True,
            ))
            continue

        diff = max(0.0, float(row.diff_time_minutes))
        latest_file_time = datetime.fromtimestamp(float(row.FileTime), tz=timezone.utc)

        statuses.append(InstrumentStatus(
            file_type=file_type,
            equipment_name=row.EquipmentName or "",
            ip=row.IP or None,
            department=department,
            latest_file_time=latest_file_time,
            diff_time_minutes=diff,
            threshold_yellow=t_yellow,
            threshold_orange=t_orange,
            threshold_red=t_red,
            is_alert=diff > t_yellow,
        ))

    logger.info("get_all_instrument_statuses: %d instruments queried", len(statuses))
    return statuses


def get_instrument_thresholds(file_type: str) -> Tuple[float, float, float]:
    return _get_thresholds().get(file_type, _default_thresholds())


def set_instrument_thresholds(file_type: str, yellow: float, orange: float, red: float) -> None:
    if any(v < 0 for v in (yellow, orange, red)):
        raise ValueError("Thresholds must be >= 0")
    _get_thresholds()[file_type] = (yellow, orange, red)
    logger.info("Thresholds updated: %s -> yellow=%.1f orange=%.1f red=%.1f", file_type, yellow, orange, red)


def list_instruments() -> list[dict]:
    thresholds = _get_thresholds()
    default = _default_thresholds()
    timeout = get_config().system.query_timeout_seconds

    try:
        with get_session("file_status") as session:
            rows = session.execute(
                text("SELECT FileType, EquipmentName FROM FileTypeList").execution_options(timeout=timeout)
            ).fetchall()
    except (OperationalError, SQLAlchemyError) as exc:
        logger.error("list_instruments: DB error: %s", exc)
        return []

    return [
        {
            "file_type": row.FileType,
            "equipment_name": row.EquipmentName or "",
            "threshold_yellow": thresholds.get(row.FileType, default)[0],
            "threshold_orange": thresholds.get(row.FileType, default)[1],
            "threshold_red":    thresholds.get(row.FileType, default)[2],
        }
        for row in rows
    ]
