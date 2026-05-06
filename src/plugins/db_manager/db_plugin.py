"""DB Manager 플러그인 — 센서/알람/공정 이력을 SQLite에 저장한다."""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from typing import Any

from src.broker import topics as T
from src.broker.message_broker import IMessageBroker
from src.plugins.plugin_interface import IPlugin

log = logging.getLogger(__name__)

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS sensor_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        INTEGER NOT NULL,
    sensor_id TEXT    NOT NULL,
    value     REAL    NOT NULL,
    unit      TEXT
);
CREATE TABLE IF NOT EXISTS alarm_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         INTEGER NOT NULL,
    alarm_id   TEXT    NOT NULL,
    severity   TEXT,
    message    TEXT,
    cleared_ts INTEGER
);
CREATE TABLE IF NOT EXISTS process_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         INTEGER NOT NULL,
    event      TEXT    NOT NULL,
    detail     TEXT
);
CREATE INDEX IF NOT EXISTS ix_sensor_log_ts ON sensor_log(ts);
CREATE INDEX IF NOT EXISTS ix_alarm_ts      ON alarm_history(ts);
"""

_BATCH_SIZE = 100
_FLUSH_INTERVAL_SEC = 5.0


class DBPlugin(IPlugin):
    """SQLite 기반 데이터 로깅 플러그인."""

    def get_name(self) -> str:    return "DBPlugin"
    def get_version(self) -> str: return "1.0.0"

    def __init__(self) -> None:
        self._broker: IMessageBroker | None = None
        self._db_path = "data/simulator.db"
        self._conn: sqlite3.Connection | None = None
        self._buffer: list[tuple] = []
        self._lock = threading.Lock()
        self._running = False
        self._flush_thread: threading.Thread | None = None

    def set_broker(self, broker: IMessageBroker) -> None:
        self._broker = broker

    def initialize(self, config: dict[str, Any]) -> bool:
        self._db_path = config.get("db_path", self._db_path)
        try:
            import pathlib
            pathlib.Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.executescript(_CREATE_TABLES)
            self._conn.commit()
            log.info("DBPlugin: DB 연결 (%s)", self._db_path)
            return True
        except Exception as e:
            log.error("DBPlugin initialize 오류: %s", e)
            return False

    def start(self) -> None:
        if not self._broker:
            return
        self._running = True
        self._broker.subscribe("sensor/", self._on_sensor)
        self._broker.subscribe(T.ALARM_NEW, self._on_alarm_new)
        self._broker.subscribe(T.ALARM_CLEAR, self._on_alarm_clear)
        self._broker.subscribe(T.RECIPE_START, self._on_process_event)
        self._broker.subscribe(T.RECIPE_COMPLETE, self._on_process_event)
        self._broker.subscribe(T.EQUIPMENT_STATE, self._on_process_event)

        self._flush_thread = threading.Thread(
            target=self._flush_loop, name="db-flush", daemon=True
        )
        self._flush_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=2.0)
        self._flush_now()

    def shutdown(self) -> None:
        self.stop()
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_publish_topics(self) -> list[str]: return []
    def get_subscribe_topics(self) -> list[str]:
        return ["sensor/", T.ALARM_NEW, T.ALARM_CLEAR,
                T.RECIPE_START, T.RECIPE_COMPLETE, T.EQUIPMENT_STATE]

    # ── 콜백 ─────────────────────────────────────────────────────────────────

    def _on_sensor(self, topic: str, payload: dict[str, Any]) -> None:
        # topic: sensor/{id}/value
        parts = topic.split("/")
        if len(parts) < 2:
            return
        sensor_id = parts[1]
        with self._lock:
            self._buffer.append((
                "sensor_log",
                (int(time.time() * 1000), sensor_id,
                 payload.get("value", 0.0), payload.get("unit", "")),
            ))
        if len(self._buffer) >= _BATCH_SIZE:
            self._flush_now()

    def _on_alarm_new(self, topic: str, payload: dict[str, Any]) -> None:
        if not self._conn:
            return
        try:
            self._conn.execute(
                "INSERT INTO alarm_history(ts, alarm_id, severity, message) VALUES(?,?,?,?)",
                (int(time.time() * 1000),
                 payload.get("id", ""), payload.get("severity", ""),
                 payload.get("message", "")),
            )
            self._conn.commit()
        except Exception as e:
            log.error("DBPlugin alarm_new 오류: %s", e)

    def _on_alarm_clear(self, topic: str, payload: dict[str, Any]) -> None:
        if not self._conn:
            return
        try:
            self._conn.execute(
                "UPDATE alarm_history SET cleared_ts=? WHERE alarm_id=? AND cleared_ts IS NULL",
                (int(time.time() * 1000), payload.get("id", "")),
            )
            self._conn.commit()
        except Exception as e:
            log.error("DBPlugin alarm_clear 오류: %s", e)

    def _on_process_event(self, topic: str, payload: dict[str, Any]) -> None:
        if not self._conn:
            return
        try:
            import json
            self._conn.execute(
                "INSERT INTO process_history(ts, event, detail) VALUES(?,?,?)",
                (int(time.time() * 1000), topic, json.dumps(payload)),
            )
            self._conn.commit()
        except Exception as e:
            log.error("DBPlugin process_event 오류: %s", e)

    # ── 배치 플러시 ───────────────────────────────────────────────────────────

    def _flush_loop(self) -> None:
        while self._running:
            time.sleep(_FLUSH_INTERVAL_SEC)
            self._flush_now()

    def _flush_now(self) -> None:
        with self._lock:
            batch = self._buffer[:]
            self._buffer.clear()
        if not batch or not self._conn:
            return
        try:
            rows = [row for table, row in batch if table == "sensor_log"]
            if rows:
                self._conn.executemany(
                    "INSERT INTO sensor_log(ts, sensor_id, value, unit) VALUES(?,?,?,?)", rows
                )
                self._conn.commit()
        except Exception as e:
            log.error("DBPlugin flush 오류: %s", e)
