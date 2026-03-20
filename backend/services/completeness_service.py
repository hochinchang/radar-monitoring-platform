"""
Completeness rate calculation service for radar-monitoring-platform.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from backend.config import get_config
from backend.database import get_session
from backend.models import CompletenessResult, TimeSeriesPoint

logger = logging.getLogger("completeness_service")

# Stores the last successful completeness result for fallback on DB error
_last_completeness: CompletenessResult | None = None

_COMPLETENESS_SQL = text("""
SELECT
    FileType,
    COUNT(*) AS actual_count,
    FLOOR(TIMESTAMPDIFF(MINUTE, :start_time, :end_time) / 10) AS expected_count,
    ROUND(
        COUNT(*) * 100.0 / NULLIF(
            FLOOR(TIMESTAMPDIFF(MINUTE, :start_time, :end_time) / 10), 0
        ),
        2
    ) AS completeness_rate
FROM FileStatus.radarStatus
WHERE FROM_UNIXTIME(FileTime) BETWEEN :start_time AND :end_time
GROUP BY FileType
""")

_TIME_SERIES_SQL = text("""
SELECT
    FROM_UNIXTIME(FileTime, '%Y-%m-%d %H:00:00') AS hour_bucket,
    COUNT(*) AS actual_count,
    FLOOR(60 / 10) AS expected_per_hour,
    ROUND(COUNT(*) * 100.0 / NULLIF(FLOOR(60 / 10), 0), 2) AS completeness_rate
FROM FileStatus.radarStatus
WHERE FROM_UNIXTIME(FileTime) BETWEEN :start_time AND :end_time
GROUP BY hour_bucket
ORDER BY hour_bucket ASC
""")


def _clamp(value: float) -> float:
    """Clamp completeness_rate to [0.0, 100.0]."""
    return max(0.0, min(100.0, value))


def calculate_completeness(start_time: datetime, end_time: datetime) -> CompletenessResult:
    """
    Calculate overall completeness rate for the given time range.

    Aggregates all FileTypes and returns the average completeness_rate.
    Returns status="no_data" if no rows found.
    Returns status="db_error" with last known value on connection failure.
    """
    global _last_completeness

    timeout = get_config().system.query_timeout_seconds

    try:
        with get_session("file_status") as session:
            result = session.execute(
                _COMPLETENESS_SQL.execution_options(timeout=timeout),
                {"start_time": start_time, "end_time": end_time},
            )
            rows = result.fetchall()

        if not rows:
            logger.info("calculate_completeness: no data for range %s – %s", start_time, end_time)
            return CompletenessResult(
                completeness_rate=0.0,
                calculated_at=datetime.now(timezone.utc),
                status="no_data",
            )

        rates = [_clamp(float(row.completeness_rate)) for row in rows if row.completeness_rate is not None]
        overall_rate = _clamp(sum(rates) / len(rates)) if rates else 0.0

        result_obj = CompletenessResult(
            completeness_rate=overall_rate,
            calculated_at=datetime.now(timezone.utc),
            status="ok",
        )
        _last_completeness = result_obj
        logger.info("calculate_completeness: rate=%.2f%% (%d FileTypes)", overall_rate, len(rows))
        return result_obj

    except (OperationalError, SQLAlchemyError) as exc:
        logger.error("calculate_completeness: DB error: %s", exc)
        if _last_completeness is not None:
            return CompletenessResult(
                completeness_rate=_last_completeness.completeness_rate,
                calculated_at=_last_completeness.calculated_at,
                status="db_error",
            )
        return CompletenessResult(
            completeness_rate=0.0,
            calculated_at=datetime.now(timezone.utc),
            status="db_error",
        )


def get_time_series(start_time: datetime, end_time: datetime) -> list[TimeSeriesPoint]:
    """
    Return hourly aggregated completeness time series.

    Marks points with completeness_rate < 90.0 as is_alert=True.
    Returns empty list on DB error.
    """
    timeout = get_config().system.query_timeout_seconds

    try:
        with get_session("file_status") as session:
            result = session.execute(
                _TIME_SERIES_SQL.execution_options(timeout=timeout),
                {"start_time": start_time, "end_time": end_time},
            )
            rows = result.fetchall()

        points: list[TimeSeriesPoint] = []
        for row in rows:
            rate = _clamp(float(row.completeness_rate)) if row.completeness_rate is not None else 0.0
            # Parse the hour_bucket string returned by MySQL
            if isinstance(row.hour_bucket, str):
                ts = datetime.strptime(row.hour_bucket, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            else:
                ts = row.hour_bucket.replace(tzinfo=timezone.utc) if row.hour_bucket.tzinfo is None else row.hour_bucket
            points.append(TimeSeriesPoint(
                timestamp=ts,
                completeness_rate=rate,
                is_alert=rate < 90.0,
            ))

        logger.info("get_time_series: %d points for range %s – %s", len(points), start_time, end_time)
        return points

    except (OperationalError, SQLAlchemyError) as exc:
        logger.error("get_time_series: DB error: %s", exc)
        return []
