import math
import random
import time

from .interfaces import IHeater, IMotor, ISensor, IValve


class SimMotor(IMotor):
    """사다리꼴 가감속 프로파일: IDLE → ACCEL → CRUISE → DECEL → DONE"""

    _PHASE_IDLE = "IDLE"
    _PHASE_ACCEL = "ACCEL"
    _PHASE_CRUISE = "CRUISE"
    _PHASE_DECEL = "DECEL"
    _PHASE_DONE = "DONE"

    def __init__(
        self,
        motor_id: str,
        max_speed: float = 100.0,
        accel: float = 50.0,
        position_range: tuple[float, float] = (0.0, 1000.0),
    ) -> None:
        self.motor_id = motor_id
        self._max_speed = max_speed
        self._speed = max_speed
        self._accel = accel  # units/s²
        self._range = position_range
        self._position = 0.0
        self._target = 0.0
        self._phase = self._PHASE_IDLE
        self._velocity = 0.0
        self._homed = False
        self._last_update = time.monotonic()

    def _update(self) -> None:
        now = time.monotonic()
        dt = now - self._last_update
        self._last_update = now
        if self._phase == self._PHASE_IDLE or self._phase == self._PHASE_DONE:
            return
        remaining = self._target - self._position
        direction = 1.0 if remaining > 0 else -1.0
        stop_dist = (self._velocity ** 2) / (2 * self._accel)

        if abs(remaining) <= stop_dist + 1e-6:
            self._phase = self._PHASE_DECEL
        elif self._velocity < self._speed:
            self._phase = self._PHASE_ACCEL

        if self._phase == self._PHASE_ACCEL:
            self._velocity = min(self._velocity + self._accel * dt, self._speed)
            if self._velocity >= self._speed:
                self._phase = self._PHASE_CRUISE
        elif self._phase == self._PHASE_DECEL:
            self._velocity = max(self._velocity - self._accel * dt, 0.0)

        delta = direction * self._velocity * dt
        if abs(delta) >= abs(remaining):
            self._position = self._target
            self._velocity = 0.0
            self._phase = self._PHASE_DONE
        else:
            self._position += delta

    def move_absolute(self, position: float) -> None:
        position = max(self._range[0], min(self._range[1], position))
        if abs(position - self._position) < 1e-6:
            self._phase = self._PHASE_DONE
            return
        self._target = position
        self._velocity = 0.0
        self._phase = self._PHASE_ACCEL
        self._last_update = time.monotonic()

    def move_relative(self, distance: float) -> None:
        self.move_absolute(self._position + distance)

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.1, speed)

    def get_position(self) -> float:
        self._update()
        return self._position

    def is_move_done(self) -> bool:
        self._update()
        return self._phase in (self._PHASE_IDLE, self._PHASE_DONE)

    def is_homed(self) -> bool:
        return self._homed

    def stop(self) -> None:
        self._target = self._position
        self._velocity = 0.0
        self._phase = self._PHASE_DONE

    def home(self) -> None:
        self._position = 0.0
        self._target = 0.0
        self._velocity = 0.0
        self._phase = self._PHASE_DONE
        self._homed = True

    def emergency_stop(self) -> None:
        self.stop()


class SimValve(IValve):
    """응답 지연 시뮬레이션 — response_ms 경과 후 상태 전환."""

    def __init__(self, valve_id: str, response_ms: int = 200) -> None:
        self.valve_id = valve_id
        self._response_ms = response_ms
        self._open = False
        self._command_open: bool | None = None
        self._command_time: float = 0.0

    def _update(self) -> None:
        if self._command_open is None:
            return
        elapsed_ms = (time.monotonic() - self._command_time) * 1000
        if elapsed_ms >= self._response_ms:
            self._open = self._command_open
            self._command_open = None

    def open(self) -> None:
        self._update()  # 대기 중인 전이를 먼저 반영
        self._command_open = True
        self._command_time = time.monotonic()

    def close(self) -> None:
        self._update()  # 대기 중인 전이를 먼저 반영
        self._command_open = False
        self._command_time = time.monotonic()

    def is_open(self) -> bool:
        self._update()
        return self._open

    def is_closed(self) -> bool:
        self._update()
        return not self._open

    def get_response_ms(self) -> int:
        return self._response_ms


class SimSensor(ISensor):
    """1차 지연(시정수 tau) + 가우시안 노이즈 센서 모델."""

    def __init__(
        self,
        sensor_id: str,
        unit: str = "",
        sensor_range: tuple[float, float] = (0.0, 100.0),
        initial_value: float = 0.0,
        noise_std: float = 0.1,
        tau: float = 5.0,
    ) -> None:
        self.sensor_id = sensor_id
        self._unit = unit
        self._range = sensor_range
        self._current = initial_value
        self._target = initial_value
        self._noise_std = noise_std
        self._tau = tau
        self._last_update = time.monotonic()
        self._healthy = True
        self._fail = False

    def set_target(self, value: float) -> None:
        self._target = value

    def set_fault(self, fail: bool) -> None:
        self._fail = fail

    def _update(self) -> None:
        now = time.monotonic()
        dt = now - self._last_update
        self._last_update = now
        if dt <= 0:
            return
        self._current += (self._target - self._current) * (dt / self._tau)
        self._current += random.gauss(0, self._noise_std)

    def read(self) -> float:
        if self._fail:
            return float("nan")
        self._update()
        return self._current

    def get_unit(self) -> str:
        return self._unit

    def get_range(self) -> tuple[float, float]:
        return self._range

    def is_healthy(self) -> bool:
        return self._healthy and not self._fail


class SimHeater(IHeater):
    """PID 응답 모델 — 1차 지연 + 오버슈트 근사."""

    def __init__(
        self,
        heater_id: str,
        power_kw: float = 10.0,
        tau: float = 30.0,
        overshoot_ratio: float = 0.05,
    ) -> None:
        self.heater_id = heater_id
        self._power_kw = power_kw
        self._tau = tau
        self._overshoot_ratio = overshoot_ratio
        self._target = 25.0
        self._current = 25.0
        self._enabled = False
        self._last_update = time.monotonic()

    def _update(self) -> None:
        now = time.monotonic()
        dt = now - self._last_update
        self._last_update = now
        if dt <= 0:
            return
        if self._enabled:
            effective_target = self._target * (1 + self._overshoot_ratio)
            self._current += (effective_target - self._current) * (dt / self._tau)
            # 오버슈트 후 수렴
            if self._current > self._target * (1 + self._overshoot_ratio * 0.5):
                self._current += (self._target - self._current) * (dt / (self._tau * 2))
        else:
            ambient = 25.0
            self._current += (ambient - self._current) * (dt / (self._tau * 3))

    def set_target(self, temperature: float) -> None:
        self._target = temperature

    def get_target(self) -> float:
        return self._target

    def get_current(self) -> float:
        self._update()
        return self._current

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def is_at_target(self, tolerance: float = 0.5) -> bool:
        self._update()
        return abs(self._current - self._target) <= tolerance
