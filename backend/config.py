"""
Configuration loader for radar-monitoring-platform.
Loads all settings from config/config.yaml using PyYAML.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import yaml

# Resolve config path: backend/ -> project root -> config/config.yaml
_CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"

logger = logging.getLogger("config")


@dataclass
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str
    pool_size: int


@dataclass
class SystemConfig:
    radar_interval_minutes: int
    query_timeout_seconds: int
    reconnect_interval_seconds: int
    max_reconnect_attempts: int
    default_max_diff_time_threshold: float


@dataclass
class InstrumentConfig:
    max_diff_time_threshold: float


@dataclass
class AppConfig:
    databases: Dict[str, DatabaseConfig]
    system: SystemConfig
    instruments: Dict[str, InstrumentConfig]


def _require(mapping: dict, key: str, context: str) -> object:
    if key not in mapping:
        raise KeyError(f"Missing required config field '{key}' in {context}")
    return mapping[key]


def _parse_database(data: dict, name: str) -> DatabaseConfig:
    ctx = f"databases.{name}"
    return DatabaseConfig(
        host=str(_require(data, "host", ctx)),
        port=int(_require(data, "port", ctx)),
        name=str(_require(data, "name", ctx)),
        user=str(_require(data, "user", ctx)),
        password=str(_require(data, "password", ctx)),
        pool_size=int(_require(data, "pool_size", ctx)),
    )


def _parse_system(data: dict) -> SystemConfig:
    ctx = "system"
    return SystemConfig(
        radar_interval_minutes=int(_require(data, "radar_interval_minutes", ctx)),
        query_timeout_seconds=int(_require(data, "query_timeout_seconds", ctx)),
        reconnect_interval_seconds=int(_require(data, "reconnect_interval_seconds", ctx)),
        max_reconnect_attempts=int(_require(data, "max_reconnect_attempts", ctx)),
        default_max_diff_time_threshold=float(
            _require(data, "default_max_diff_time_threshold", ctx)
        ),
    )


def _load_config(path: Path = _CONFIG_PATH) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError("config.yaml must be a YAML mapping at the top level")

    # Databases
    db_raw = _require(raw, "databases", "root")
    required_dbs = ("file_status", "system_status", "disk_status")
    databases: Dict[str, DatabaseConfig] = {}
    for db_name in required_dbs:
        if db_name not in db_raw:
            raise KeyError(f"Missing required database config: databases.{db_name}")
        databases[db_name] = _parse_database(db_raw[db_name], db_name)

    # System
    system = _parse_system(_require(raw, "system", "root"))

    # Instruments (optional entries, but section must exist)
    instruments_raw = _require(raw, "instruments", "root")
    instruments: Dict[str, InstrumentConfig] = {}
    for key, val in instruments_raw.items():
        if val is None:
            logger.warning("instruments.%s has no value, using default threshold", key)
            val = {}
        instruments[key] = InstrumentConfig(
            max_diff_time_threshold=float(
                val.get("max_diff_time_threshold",
                        raw.get("system", {}).get("default_max_diff_time_threshold", 30.0))
            )
        )

    return AppConfig(databases=databases, system=system, instruments=instruments)


# Singleton — loaded once at startup
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Return the singleton AppConfig, loading it on first call."""
    global _config
    if _config is None:
        _config = _load_config()
    return _config
