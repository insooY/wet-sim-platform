"""Fault Injection 시스템 — HAL 디바이스에 이상 상황을 인위적으로 주입한다."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from src.hal.hal_manager import HALManager

log = logging.getLogger(__name__)


class FaultType(Enum):
    SENSOR_FAIL   = auto()   # 센서 값 NaN (단선)
    SENSOR_DRIFT  = auto()   # 센서 점진적 오프셋
    VALVE_STUCK   = auto()   # 밸브 명령 무시
    VALVE_LEAK    = auto()   # 닫힌 밸브 미세 유량
    MOTOR_ERROR   = auto()   # 모터 이동 거부
    COMM_TIMEOUT  = auto()   # 통신 지연 (시뮬레이션)


@dataclass
class Fault:
    fault_type: FaultType
    device_id: str
    params: dict[str, Any] = field(default_factory=dict)
    active: bool = True


class FaultInjector:
    """HALManager에 Fault를 주입/제거한다.

    Standalone 모드 전용. EquipmentManager.tick()과 동일 주기로 apply()를 호출한다.
    """

    def __init__(self, hal: HALManager) -> None:
        self._hal = hal
        self._faults: dict[str, Fault] = {}   # key: f"{type.name}:{device_id}"

    # ── 주입 / 제거 ───────────────────────────────────────────────────────────

    def inject(self, fault_type: FaultType, device_id: str,
               params: dict[str, Any] | None = None) -> str:
        """Fault를 추가하고 key를 반환한다."""
        key = f"{fault_type.name}:{device_id}"
        self._faults[key] = Fault(fault_type, device_id, params or {})
        log.warning("Fault 주입: %s → %s", fault_type.name, device_id)
        self._apply_immediate(self._faults[key])
        return key

    def remove(self, key: str) -> None:
        fault = self._faults.pop(key, None)
        if fault:
            log.info("Fault 제거: %s", key)
            self._restore(fault)

    def remove_all(self) -> None:
        for key in list(self._faults):
            self.remove(key)

    def active_faults(self) -> list[Fault]:
        return [f for f in self._faults.values() if f.active]

    def is_active(self, fault_type: FaultType, device_id: str) -> bool:
        return f"{fault_type.name}:{device_id}" in self._faults

    # ── tick 적용 ─────────────────────────────────────────────────────────────

    def apply(self) -> None:
        """매 tick마다 지속형 Fault를 유지/적용한다."""
        for fault in list(self._faults.values()):
            if fault.fault_type == FaultType.SENSOR_DRIFT:
                self._apply_drift(fault)

    # ── 즉시 적용 ─────────────────────────────────────────────────────────────

    def _apply_immediate(self, fault: Fault) -> None:
        ft = fault.fault_type
        dev = fault.device_id

        if ft == FaultType.SENSOR_FAIL:
            sensor = self._hal.all_sensors().get(dev)
            if sensor and hasattr(sensor, "set_fault"):
                sensor.set_fault(True)

        elif ft == FaultType.VALVE_STUCK:
            valve = self._hal.all_valves().get(dev)
            if valve and hasattr(valve, "set_stuck"):
                valve.set_stuck(True)

        elif ft == FaultType.MOTOR_ERROR:
            motor = self._hal.all_motors().get(dev)
            if motor and hasattr(motor, "set_error"):
                motor.set_error(True)

    def _apply_drift(self, fault: Fault) -> None:
        sensor = self._hal.all_sensors().get(fault.device_id)
        if sensor and hasattr(sensor, "add_offset"):
            rate = fault.params.get("rate_per_tick", 0.01)
            sensor.add_offset(rate)

    def _restore(self, fault: Fault) -> None:
        ft = fault.fault_type
        dev = fault.device_id

        if ft == FaultType.SENSOR_FAIL:
            sensor = self._hal.all_sensors().get(dev)
            if sensor and hasattr(sensor, "set_fault"):
                sensor.set_fault(False)

        elif ft == FaultType.SENSOR_DRIFT:
            sensor = self._hal.all_sensors().get(dev)
            if sensor and hasattr(sensor, "reset_offset"):
                sensor.reset_offset()

        elif ft == FaultType.VALVE_STUCK:
            valve = self._hal.all_valves().get(dev)
            if valve and hasattr(valve, "set_stuck"):
                valve.set_stuck(False)

        elif ft == FaultType.MOTOR_ERROR:
            motor = self._hal.all_motors().get(dev)
            if motor and hasattr(motor, "set_error"):
                motor.set_error(False)
