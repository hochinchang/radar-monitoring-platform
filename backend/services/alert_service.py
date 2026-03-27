"""
Alert service for radar-monitoring-platform.
Queries radarFileCheck for each instrument's latest snapshot,
calculates diff_time_minutes, and compares against per-instrument thresholds.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from backend.config import get_config
from backend.database import get_session
from backend.models import InstrumentStatus

logger = logging.getLogger("alert_service")

# Runtime threshold store: file_type -> threshold (minutes)
# Initialised from config.yaml on first access; persists in memory until restart.
_thresholds: dict[str, float] = {}

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


def _load_ip_department_map() -> dict[str, str]:
    """Load IP -> Department mapping from SystemStatus DB."""
    try:
        with get_session("system_status") as session:
            rows = session.execute(_SYSTEM_IP_DEPT_SQL).fetchall()
        return {row.IP: (row.Department or "") for row in rows}
    except Exception as exc:
        logger.warning("Failed to load IP->Department map: %s", exc)
        return {}


def _get_thresholds() -> dict[str, float]:
    """Return the in-memory threshold store, seeding from config on first call."""
    if not _thresholds:
        cfg = get_config()
        default = cfg.system.default_max_diff_time_threshold
        for file_type, inst_cfg in cfg.instruments.items():
            _thresholds[file_type] = inst_cfg.max_diff_time_threshold
        logger.info(
            "Thresholds initialised from config: %d instruments, default=%.1f min",
            len(_thresholds), default,
        )
    return _thresholds


def get_all_instrument_statuses() -> list[InstrumentStatus]:
    thresholds = _get_thresholds()
    default_threshold = get_config().system.default_max_diff_time_threshold
    timeout = get_config().system.query_timeout_seconds
    ip_dept = _load_ip_department_map()

    try:
        with get_session("file_status") as session:
            result = session.execute(
                _INSTRUMENT_STATUS_SQL.execution_options(timeout=timeout)
            )
            rows = result.fetchall()
    except (OperationalError, SQLAlchemyError) as exc:
        logger.error("get_all_instrument_statuses: DB error: %s", exc)
        return []

    statuses: list[InstrumentStatus] = []
    for row in rows:
        file_type: str = row.FileType
        threshold = thresholds.get(file_type, default_threshold)
        department = ip_dept.get(row.IP or "", "") or None

        if row.FileTime is None or row.diff_time_minutes is None:
            statuses.append(InstrumentStatus(
                file_type=file_type,
                equipment_name=row.EquipmentName or "",
                ip=row.IP or None,
                department=department,
                latest_file_time=None,
                diff_time_minutes=None,
                max_diff_time_threshold=threshold,
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
            max_diff_time_threshold=threshold,
            is_alert=diff > threshold,
        ))

    logger.info("get_all_instrument_statuses: %d instruments queried", len(statuses))
    return statuses


def get_instrument_threshold(file_type: str) -> float:
    """Return the current threshold for the given file_type."""
    thresholds = _get_thresholds()
    default = get_config().system.default_max_diff_time_threshold
    return thresholds.get(file_type, default)


def set_instrument_threshold(file_type: str, threshold_minutes: float) -> None:
    """Update the in-memory threshold for the given file_type."""
    if threshold_minutes < 0:
        raise ValueError(f"threshold_minutes must be >= 0, got {threshold_minutes}")
    _get_thresholds()[file_type] = threshold_minutes
    logger.info("Threshold updated: %s -> %.1f min", file_type, threshold_minutes)


def list_instruments() -> list[dict]:
    """
    Return all instruments from FileTypeList with their current thresholds.
    Used by the instruments router to populate the instrument list.
    """
    thresholds = _get_thresholds()
    default = get_config().system.default_max_diff_time_threshold
    timeout = get_config().system.query_timeout_seconds

    try:
        with get_session("file_status") as session:
            result = session.execute(
                text("SELECT FileType, EquipmentName FROM FileTypeList").execution_options(timeout=timeout)
            )
            rows = result.fetchall()
    except (OperationalError, SQLAlchemyError) as exc:
        logger.error("list_instruments: DB error: %s", exc)
        return []

    return [
        {
            "file_type": row.FileType,
            "equipment_name": row.EquipmentName or "",
            "max_diff_time_threshold": thresholds.get(row.FileType, default),
        }
        for row in rows
    ]
