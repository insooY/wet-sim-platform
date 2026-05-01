import time
from enum import Enum, auto
from typing import Any, Callable

from src.hal.hal_manager import HALManager


class StepState(Enum):
    PENDING = auto()
    RUNNING = auto()
    DONE = auto()
    FAILED = auto()


class RecipeEngine:
    """YAML 레시피를 순차 실행한다.

    각 스텝은 다음 키를 가질 수 있다:
      name       표시명 (필수)
      duration   대기 시간(초)
      valves_open   열 밸브 ID 목록
      valves_close  닫을 밸브 ID 목록
      motor_moves   [{id, position}] 이동 목록
      heater_setpoints [{id, temperature}]
      wait_heater     [{id, tolerance}] 온도 도달 대기
    """

    def __init__(self, hal: HALManager) -> None:
        self._hal = hal
        self._steps: list[dict[str, Any]] = []
        self._current_index = 0
        self._step_start_time = 0.0
        self._state = StepState.PENDING
        self._on_step_change: Callable[[int, str], None] | None = None

    def load(self, recipe: dict[str, Any]) -> None:
        self._steps = recipe.get("steps", [])
        self._current_index = 0
        self._state = StepState.PENDING

    def set_step_callback(self, fn: Callable[[int, str], None]) -> None:
        """스텝 전환 시 fn(step_index, step_name) 호출."""
        self._on_step_change = fn

    def start(self) -> None:
        self._current_index = 0
        self._state = StepState.RUNNING
        self._execute_step(self._current_index)

    def tick(self) -> bool:
        """주기적으로 호출 — 현재 스텝 완료 여부를 확인하고 다음으로 넘긴다.
        Returns True if recipe is still running, False when done or failed."""
        if self._state != StepState.RUNNING:
            return False
        if not self._steps:
            self._state = StepState.DONE
            return False

        step = self._steps[self._current_index]
        if self._step_complete(step):
            self._current_index += 1
            if self._current_index >= len(self._steps):
                self._state = StepState.DONE
                return False
            self._execute_step(self._current_index)
        return True

    def abort(self) -> None:
        self._state = StepState.FAILED
        for _, valve in self._hal.all_valves().items():
            valve.close()

    @property
    def current_step_index(self) -> int:
        return self._current_index

    @property
    def current_step_name(self) -> str:
        if not self._steps or self._current_index >= len(self._steps):
            return ""
        return self._steps[self._current_index].get("name", f"Step {self._current_index}")

    @property
    def is_done(self) -> bool:
        return self._state == StepState.DONE

    @property
    def total_steps(self) -> int:
        return len(self._steps)

    # ── 내부 ────────────────────────────────────────────────────────────────

    def _execute_step(self, index: int) -> None:
        step = self._steps[index]
        self._step_start_time = time.monotonic()

        for vid in step.get("valves_open", []):
            self._hal.get_valve(vid).open()
        for vid in step.get("valves_close", []):
            self._hal.get_valve(vid).close()
        for move in step.get("motor_moves", []):
            self._hal.get_motor(move["id"]).move_absolute(move["position"])
        for hs in step.get("heater_setpoints", []):
            h = self._hal.get_heater(hs["id"])
            h.set_target(hs["temperature"])
            h.enable()

        if self._on_step_change:
            self._on_step_change(index, step.get("name", f"Step {index}"))

    def _step_complete(self, step: dict[str, Any]) -> bool:
        elapsed = time.monotonic() - self._step_start_time
        duration = step.get("duration", 0)
        if elapsed < duration:
            return False
        for move in step.get("motor_moves", []):
            if not self._hal.get_motor(move["id"]).is_move_done():
                return False
        for wh in step.get("wait_heater", []):
            tol = wh.get("tolerance", 1.0)
            if not self._hal.get_heater(wh["id"]).is_at_target(tol):
                return False
        return True
