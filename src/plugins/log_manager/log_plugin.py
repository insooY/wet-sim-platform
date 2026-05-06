"""Log Manager 플러그인 — 카테고리별 파일 로깅 + 일별 로테이션."""
from __future__ import annotations

import logging
import logging.handlers
import pathlib
from typing import Any

from src.broker import topics as T
from src.broker.message_broker import IMessageBroker
from src.plugins.plugin_interface import IPlugin

log = logging.getLogger(__name__)


class LogPlugin(IPlugin):
    """파일 기반 구조적 로깅 플러그인."""

    def get_name(self) -> str:    return "LogPlugin"
    def get_version(self) -> str: return "1.0.0"

    def __init__(self) -> None:
        self._broker: IMessageBroker | None = None
        self._log_dir = pathlib.Path("logs")
        self._max_bytes = 10 * 1024 * 1024   # 10 MB
        self._backup_count = 7
        self._loggers: dict[str, logging.Logger] = {}

    def set_broker(self, broker: IMessageBroker) -> None:
        self._broker = broker

    def initialize(self, config: dict[str, Any]) -> bool:
        self._log_dir = pathlib.Path(config.get("log_dir", "logs"))
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._max_bytes   = config.get("max_bytes",    self._max_bytes)
        self._backup_count = config.get("backup_count", self._backup_count)
        # 카테고리별 로거 초기화
        for category in ("sensor", "alarm", "process", "system"):
            self._loggers[category] = self._make_logger(category)
        log.info("LogPlugin: 로그 디렉터리 (%s)", self._log_dir)
        return True

    def start(self) -> None:
        if not self._broker:
            return
        self._broker.subscribe("sensor/",          self._on_sensor)
        self._broker.subscribe(T.ALARM_NEW,         self._on_alarm)
        self._broker.subscribe(T.ALARM_CLEAR,       self._on_alarm)
        self._broker.subscribe(T.EQUIPMENT_STATE,   self._on_system)
        self._broker.subscribe(T.RECIPE_START,      self._on_process)
        self._broker.subscribe(T.RECIPE_STEP,       self._on_process)
        self._broker.subscribe(T.RECIPE_COMPLETE,   self._on_process)
        self._broker.subscribe(T.SYSTEM_HEARTBEAT,  self._on_system)

    def stop(self) -> None:
        pass

    def shutdown(self) -> None:
        for logger in self._loggers.values():
            for h in logger.handlers[:]:
                h.close()
                logger.removeHandler(h)

    def get_publish_topics(self) -> list[str]: return []
    def get_subscribe_topics(self) -> list[str]:
        return ["sensor/", T.ALARM_NEW, T.ALARM_CLEAR,
                T.EQUIPMENT_STATE, T.RECIPE_START, T.RECIPE_STEP,
                T.RECIPE_COMPLETE, T.SYSTEM_HEARTBEAT]

    # ── 콜백 ─────────────────────────────────────────────────────────────────

    def _on_sensor(self, topic: str, payload: dict[str, Any]) -> None:
        self._log("sensor", f"{topic} {payload}")

    def _on_alarm(self, topic: str, payload: dict[str, Any]) -> None:
        self._log("alarm", f"{topic} id={payload.get('id')} sev={payload.get('severity')} {payload.get('message','')}")

    def _on_process(self, topic: str, payload: dict[str, Any]) -> None:
        self._log("process", f"{topic} {payload}")

    def _on_system(self, topic: str, payload: dict[str, Any]) -> None:
        self._log("system", f"{topic} {payload}")

    # ── 내부 ─────────────────────────────────────────────────────────────────

    def _log(self, category: str, message: str) -> None:
        logger = self._loggers.get(category)
        if logger:
            logger.info(message)

    def _make_logger(self, category: str) -> logging.Logger:
        name = f"wetsim.{category}"
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        if not logger.handlers:
            path = self._log_dir / f"{category}.log"
            handler = logging.handlers.RotatingFileHandler(
                path, maxBytes=self._max_bytes,
                backupCount=self._backup_count, encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            ))
            logger.addHandler(handler)
        return logger
