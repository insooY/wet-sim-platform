"""Alarm Manager 플러그인 — 센서 조건 판정 + 인터락 트리거."""
from __future__ import annotations

import logging
import operator
import re
from typing import Any

from src.broker import topics as T
from src.broker.message_broker import IMessageBroker
from src.plugins.plugin_interface import IPlugin

log = logging.getLogger(__name__)

# 지원하는 비교 연산자
_OPS = {
    ">":  operator.gt,
    ">=": operator.ge,
    "<":  operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}

_COND_RE = re.compile(r"^\s*(>=|<=|>|<|==|!=)\s*([\d.]+)\s*$")


class AlarmPlugin(IPlugin):
    """alarm.yaml 기반 알람 조건 판정 플러그인."""

    def get_name(self) -> str:    return "AlarmPlugin"
    def get_version(self) -> str: return "1.0.0"

    def __init__(self) -> None:
        self._broker: IMessageBroker | None = None
        self._alarms: list[dict[str, Any]] = []
        # {alarm_id: bool} — 현재 활성화 상태
        self._active: dict[str, bool] = {}

    def set_broker(self, broker: IMessageBroker) -> None:
        self._broker = broker

    def initialize(self, config: dict[str, Any]) -> bool:
        self._alarms = config.get("alarms", [])
        for alarm in self._alarms:
            self._active[alarm["id"]] = False
        log.info("AlarmPlugin: %d개 알람 규칙 로드", len(self._alarms))
        return True

    def start(self) -> None:
        if self._broker:
            self._broker.subscribe("sensor/", self._on_sensor)

    def stop(self) -> None:
        pass

    def shutdown(self) -> None:
        self._active.clear()

    def get_publish_topics(self) -> list[str]:
        return [T.ALARM_NEW, T.ALARM_CLEAR, T.INTERLOCK_TRIGGER]

    def get_subscribe_topics(self) -> list[str]:
        return ["sensor/"]

    # ── 콜백 ─────────────────────────────────────────────────────────────────

    def _on_sensor(self, topic: str, payload: dict[str, Any]) -> None:
        # topic: sensor/{id}/value
        parts = topic.split("/")
        if len(parts) < 2:
            return
        sensor_id = parts[1]
        value = payload.get("value")
        if value is None:
            return

        for alarm in self._alarms:
            if alarm.get("sensor") != sensor_id:
                continue
            alarm_id = alarm["id"]
            triggered = self._evaluate(alarm.get("condition", ""), value)
            was_active = self._active.get(alarm_id, False)

            if triggered and not was_active:
                self._active[alarm_id] = True
                self._fire_alarm(alarm, value)
            elif not triggered and was_active:
                self._active[alarm_id] = False
                self._clear_alarm(alarm_id)

    # ── 내부 ─────────────────────────────────────────────────────────────────

    def _evaluate(self, condition: str, value: float) -> bool:
        m = _COND_RE.match(condition)
        if not m:
            return False
        op_str, threshold_str = m.group(1), m.group(2)
        op = _OPS.get(op_str)
        if op is None:
            return False
        try:
            return op(value, float(threshold_str))
        except (ValueError, TypeError):
            return False

    def _fire_alarm(self, alarm: dict[str, Any], value: float) -> None:
        if not self._broker:
            return
        alarm_id = alarm["id"]
        severity = alarm.get("severity", "warning")
        log.warning("알람 발생: %s [%s] value=%.3f cond=%s",
                    alarm_id, severity, value, alarm.get("condition", ""))
        self._broker.publish(T.ALARM_NEW, {
            "id":        alarm_id,
            "severity":  severity,
            "sensor":    alarm.get("sensor", ""),
            "condition": alarm.get("condition", ""),
            "value":     value,
            "message":   f"{alarm_id}: {alarm.get('sensor','')} {alarm.get('condition','')} (현재={value:.3f})",
        })
        if alarm.get("interlock", False):
            self._broker.publish(T.INTERLOCK_TRIGGER, {
                "alarm_id": alarm_id, "severity": severity
            })

    def _clear_alarm(self, alarm_id: str) -> None:
        if not self._broker:
            return
        log.info("알람 해제: %s", alarm_id)
        self._broker.publish(T.ALARM_CLEAR, {"id": alarm_id})
