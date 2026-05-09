"""State Reporter — HAL 상태를 ZeroMQ PUB으로 주기적으로 발행한다."""
from __future__ import annotations

import json
import logging
import math
import time
from typing import Any

from src.broker import topics as T
from src.hal.hal_manager import HALManager

log = logging.getLogger(__name__)


class StateReporter:
    """HAL 전체 상태를 읽어 ZMQ PUB 소켓으로 발행한다.

    Qt QTimer 또는 외부 tick 루프에서 report() 를 주기적으로 호출한다.
    """

    def __init__(self, hal: HALManager, pub_socket: Any) -> None:
        self._hal = hal
        self._pub = pub_socket   # zmq PUB socket (or None for inproc)
        self._log_sink: list[dict] | None = None  # 메시지 로그 연결용

    def set_log_sink(self, sink: list[dict]) -> None:
        """발행된 메시지를 기록할 리스트를 연결한다."""
        self._log_sink = sink

    # ── 발행 루프 ─────────────────────────────────────────────────────────────

    def report(self) -> None:
        """센서·밸브·모터·히터 전체 상태를 한 번 발행한다."""
        ts = int(time.time() * 1000)
        for sid, sensor in self._hal.all_sensors().items():
            val = sensor.read()
            if not math.isnan(val):
                self._publish(T.sensor_value(sid), {
                    "value": round(val, 4),
                    "unit": sensor.get_unit(),
                    "quality": "good" if sensor.is_healthy() else "bad",
                }, ts)
            else:
                self._publish(T.sensor_value(sid), {
                    "value": None, "unit": sensor.get_unit(), "quality": "fail"
                }, ts)

        for vid, valve in self._hal.all_valves().items():
            self._publish(T.valve_state(vid), {"open": valve.is_open()}, ts)

        for mid, motor in self._hal.all_motors().items():
            self._publish(T.motor_position(mid), {
                "position": round(motor.get_position(), 4),
                "done": motor.is_move_done(),
            }, ts)

        for hid, heater in self._hal.all_heaters().items():
            self._publish(T.heater_temp(hid), {
                "current": round(heater.get_current(), 4),
                "target":  heater.get_target(),
                "at_target": heater.is_at_target(),
            }, ts)

    def publish_equipment_state(self, state_name: str) -> None:
        self._publish(T.EQUIPMENT_STATE, {"state": state_name})

    def publish_recipe_step(self, index: int, name: str, total: int) -> None:
        self._publish(T.RECIPE_STEP, {"index": index, "name": name, "total": total})

    def publish_alarm(self, alarm_id: str, severity: str, message: str) -> None:
        self._publish(T.ALARM_NEW, {
            "id": alarm_id, "severity": severity, "message": message
        })

    # ── 내부 ─────────────────────────────────────────────────────────────────

    def _publish(self, topic: str, payload: dict[str, Any],
                 ts: int | None = None) -> None:
        if ts is None:
            ts = int(time.time() * 1000)
        msg = {"topic": topic, "timestamp": ts, "payload": payload}
        if self._pub:
            try:
                self._pub.send_string(json.dumps(msg), flags=0)
            except Exception as e:
                log.debug("StateReporter publish 오류: %s", e)
        if self._log_sink is not None:
            self._log_sink.append({"dir": "TX", "ts": ts, "topic": topic, "payload": payload})
