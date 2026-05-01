from typing import Any

from .interfaces import IHeater, IMotor, ISensor, IValve
from .simulator_hal import SimHeater, SimMotor, SimSensor, SimValve


class HALManager:
    """YAML equipment.yaml 설정에서 HAL 인스턴스를 생성하고 ID로 조회한다."""

    def __init__(self) -> None:
        self._motors: dict[str, IMotor] = {}
        self._valves: dict[str, IValve] = {}
        self._sensors: dict[str, ISensor] = {}
        self._heaters: dict[str, IHeater] = {}

    def load_from_config(self, config: dict[str, Any]) -> None:
        """equipment.yaml의 motors/valves/sensors/heaters 섹션을 읽어 인스턴스를 생성한다."""
        for m in config.get("motors", []):
            self._motors[m["id"]] = self._build_motor(m)
        for v in config.get("valves", []):
            self._valves[v["id"]] = self._build_valve(v)
        for s in config.get("sensors", []):
            self._sensors[s["id"]] = self._build_sensor(s)
        for h in config.get("heaters", []):
            self._heaters[h["id"]] = self._build_heater(h)

    # ── 빌더 ─────────────────────────────────────────────────────────────────

    def _build_motor(self, cfg: dict) -> IMotor:
        r = cfg.get("range", [0, 1000])
        return SimMotor(
            motor_id=cfg["id"],
            max_speed=cfg.get("max_speed", 100.0),
            accel=cfg.get("accel", 50.0),
            position_range=(r[0], r[1]),
        )

    def _build_valve(self, cfg: dict) -> IValve:
        return SimValve(
            valve_id=cfg["id"],
            response_ms=cfg.get("response_ms", 200),
        )

    def _build_sensor(self, cfg: dict) -> ISensor:
        sim = cfg.get("simulation", {})
        r = cfg.get("range", [0, 100])
        return SimSensor(
            sensor_id=cfg["id"],
            unit=cfg.get("unit", ""),
            sensor_range=(r[0], r[1]),
            initial_value=cfg.get("initial_value", (r[0] + r[1]) / 2),
            noise_std=sim.get("noise", 0.1),
            tau=sim.get("response_tau", 5.0),
        )

    def _build_heater(self, cfg: dict) -> IHeater:
        return SimHeater(
            heater_id=cfg["id"],
            power_kw=cfg.get("power_kw", 10.0),
            tau=cfg.get("tau", 30.0),
        )

    # ── 조회 ─────────────────────────────────────────────────────────────────

    def get_motor(self, motor_id: str) -> IMotor:
        return self._motors[motor_id]

    def get_valve(self, valve_id: str) -> IValve:
        return self._valves[valve_id]

    def get_sensor(self, sensor_id: str) -> ISensor:
        return self._sensors[sensor_id]

    def get_heater(self, heater_id: str) -> IHeater:
        return self._heaters[heater_id]

    def all_motors(self) -> dict[str, IMotor]:
        return dict(self._motors)

    def all_valves(self) -> dict[str, IValve]:
        return dict(self._valves)

    def all_sensors(self) -> dict[str, ISensor]:
        return dict(self._sensors)

    def all_heaters(self) -> dict[str, IHeater]:
        return dict(self._heaters)
