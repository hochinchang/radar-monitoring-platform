"""
System status service — queries SystemStatus and DiskStatus databases.
Groups results by Department from SystemIPList.
"""
from __future__ import annotations
import logging
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from backend.config import get_config
from backend.database import get_session

logger = logging.getLogger("system_service")

_SYSTEM_SQL = text("""
SELECT cl.IP, cl.Load_1, cl.Load_5, cl.LOAD_15, cl.MemoryUSE,
       sl.EquipmentName, sl.Department
FROM CheckList cl
LEFT JOIN SystemIPList sl ON cl.IP = sl.IP
""")

_DISK_SQL = text("""
SELECT cl.IP, cl.FileSystem, cl.Used,
       sl.EquipmentName, sl.Department
FROM CheckList cl
LEFT JOIN SystemIPList sl ON cl.IP = sl.IP
""")


def get_system_status() -> list[dict]:
    timeout = get_config().system.query_timeout_seconds
    try:
        with get_session("system_status") as session:
            rows = session.execute(_SYSTEM_SQL.execution_options(timeout=timeout)).fetchall()
        return [
            {
                "ip": row.IP,
                "equipment_name": row.EquipmentName or row.IP,
                "department": row.Department or "",
                "load_1":     float(row.Load_1)    if row.Load_1    is not None else None,
                "load_5":     float(row.Load_5)    if row.Load_5    is not None else None,
                "load_15":    float(row.LOAD_15)   if row.LOAD_15   is not None else None,
                "memory_use": float(row.MemoryUSE) if row.MemoryUSE is not None else None,
            }
            for row in rows
        ]
    except (OperationalError, SQLAlchemyError) as exc:
        logger.error("get_system_status: DB error: %s", exc)
        return []


def get_disk_status() -> list[dict]:
    timeout = get_config().system.query_timeout_seconds
    try:
        with get_session("disk_status") as session:
            rows = session.execute(_DISK_SQL.execution_options(timeout=timeout)).fetchall()
        # DiskStatus.CheckList 沒有 SystemIPList，需從 system_status 取 Department
        # 先取 IP->Department map
        dept_map = _load_dept_map()
        return [
            {
                "ip": row.IP,
                "file_system": row.FileSystem,
                "used_pct": float(row.Used) if row.Used is not None else None,
                "equipment_name": dept_map.get(row.IP, {}).get("equipment_name", row.IP),
                "department": dept_map.get(row.IP, {}).get("department", ""),
            }
            for row in rows
        ]
    except (OperationalError, SQLAlchemyError) as exc:
        logger.error("get_disk_status: DB error: %s", exc)
        return []


def _load_dept_map() -> dict[str, dict]:
    """Load IP -> {department, equipment_name} from SystemIPList."""
    try:
        with get_session("system_status") as session:
            rows = session.execute(
                text("SELECT IP, EquipmentName, Department FROM SystemIPList")
            ).fetchall()
        return {
            row.IP: {"department": row.Department or "", "equipment_name": row.EquipmentName or row.IP}
            for row in rows
        }
    except Exception as exc:
        logger.warning("_load_dept_map: %s", exc)
        return {}
