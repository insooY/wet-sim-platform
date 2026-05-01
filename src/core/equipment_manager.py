from typing import Any, Callable

from src.hal.hal_manager import HALManager
from .fsm import EquipmentFSM, EquipmentState
from .recipe_engine import RecipeEngine


class EquipmentManager:
    """HAL + FSM + RecipeEngine을 통합하는 장비 최상위 관리자."""

    def __init__(self, hal: HALManager) -> None:
        self._hal = hal
        self._fsm = EquipmentFSM()
        self._recipe = RecipeEngine(hal)
        self._fsm.add_listener(self._on_state_change)

    # ── 공개 API ─────────────────────────────────────────────────────────────

    def initialize(self) -> bool:
        if not self._fsm.transition(EquipmentState.INITIALIZING):
            return False
        for motor in self._hal.all_motors().values():
            motor.home()
        for valve in self._hal.all_valves().values():
            valve.close()
        self._fsm.transition(EquipmentState.READY)
        return True

    def start_recipe(self, recipe: dict[str, Any]) -> bool:
        if not self._fsm.is_ready():
            return False
        self._recipe.load(recipe)
        self._fsm.transition(EquipmentState.RUNNING)
        self._recipe.start()
        return True

    def tick(self) -> None:
        """주기적으로 호출 (예: 100 ms 타이머). 레시피 진행 및 완료 감지."""
        if not self._fsm.is_running():
            return
        still_running = self._recipe.tick()
        if not still_running:
            self._fsm.transition(EquipmentState.IDLE)

    def pause(self) -> bool:
        return self._fsm.transition(EquipmentState.PAUSED)

    def resume(self) -> bool:
        return self._fsm.transition(EquipmentState.RUNNING)

    def abort(self) -> None:
        self._recipe.abort()
        self._fsm.transition(EquipmentState.ABORTING)
        self._fsm.transition(EquipmentState.IDLE)

    def emergency_stop(self) -> None:
        for motor in self._hal.all_motors().values():
            motor.emergency_stop()
        for valve in self._hal.all_valves().values():
            valve.close()
        self._recipe.abort()
        self._fsm.force(EquipmentState.IDLE)

    def add_state_listener(self, fn: Callable[[EquipmentState, EquipmentState], None]) -> None:
        self._fsm.add_listener(fn)

    def set_step_callback(self, fn: Callable[[int, str], None]) -> None:
        self._recipe.set_step_callback(fn)

    @property
    def state(self) -> EquipmentState:
        return self._fsm.state

    @property
    def recipe_progress(self) -> tuple[int, int]:
        return self._recipe.current_step_index, self._recipe.total_steps

    @property
    def current_step_name(self) -> str:
        return self._recipe.current_step_name

    # ── 내부 ─────────────────────────────────────────────────────────────────

    def _on_state_change(self, old: EquipmentState, new: EquipmentState) -> None:
        pass
