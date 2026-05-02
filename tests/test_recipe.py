import time

import pytest

from src.core.recipe_engine import RecipeEngine, StepState
from src.hal.hal_manager import HALManager


EQUIPMENT_CFG = {
    "motors":  [{"id": "M1", "max_speed": 2000.0, "accel": 10000.0, "range": [0, 500]}],
    "valves":  [{"id": "V1", "response_ms": 50}, {"id": "V2", "response_ms": 50}],
    "sensors": [{"id": "S1", "unit": "°C", "range": [0, 100],
                 "simulation": {"noise": 0.0, "response_tau": 1.0}}],
    "heaters": [{"id": "H1", "power_kw": 5.0, "tau": 1.0}],
}

SIMPLE_RECIPE = {
    "steps": [
        {"name": "Open V1",    "valves_open": ["V1"], "duration": 0.05},
        {"name": "Close V1",   "valves_close": ["V1"], "duration": 0.05},
        {"name": "Move M1",    "motor_moves": [{"id": "M1", "position": 100.0}], "duration": 0},
    ]
}


def make_hal() -> HALManager:
    hal = HALManager()
    hal.load_from_config(EQUIPMENT_CFG)
    return hal


class TestRecipeEngine:
    def test_initial_state_pending(self):
        engine = RecipeEngine(make_hal())
        engine.load(SIMPLE_RECIPE)
        assert not engine.is_done
        assert engine.total_steps == 3

    def test_start_sets_running(self):
        engine = RecipeEngine(make_hal())
        engine.load(SIMPLE_RECIPE)
        engine.start()
        assert engine.current_step_index == 0
        assert engine.current_step_name == "Open V1"

    def test_tick_advances_steps(self):
        hal = make_hal()
        engine = RecipeEngine(hal)
        engine.load(SIMPLE_RECIPE)
        engine.start()

        # Step 0: duration 0.05s — 0.1초 대기 후 tick
        time.sleep(0.1)
        engine.tick()
        assert engine.current_step_index == 1

    def test_recipe_completes(self):
        hal = make_hal()
        engine = RecipeEngine(hal)
        engine.load(SIMPLE_RECIPE)
        engine.start()

        deadline = time.monotonic() + 5.0
        while not engine.is_done:
            engine.tick()
            assert time.monotonic() < deadline, "Recipe did not complete in time"

        assert engine.is_done

    def test_valve_opened_after_step(self):
        hal = make_hal()
        engine = RecipeEngine(hal)
        engine.load(SIMPLE_RECIPE)
        engine.start()

        # Step 0 실행 직후 V1이 열려 있어야 함 (response_ms=50 이상 대기)
        time.sleep(0.1)
        assert hal.get_valve("V1").is_open()

    def test_valve_closed_after_close_step(self):
        hal = make_hal()
        engine = RecipeEngine(hal)
        engine.load(SIMPLE_RECIPE)
        engine.start()

        # Step 0 (open) → Step 1 (close) 완료 대기
        deadline = time.monotonic() + 3.0
        while engine.current_step_index < 2:
            engine.tick()
            assert time.monotonic() < deadline
        time.sleep(0.1)  # valve response delay
        assert hal.get_valve("V1").is_closed()

    def test_step_callback_called(self):
        engine = RecipeEngine(make_hal())
        engine.load(SIMPLE_RECIPE)
        events: list[tuple[int, str]] = []
        engine.set_step_callback(lambda i, n: events.append((i, n)))
        engine.start()

        assert events[0] == (0, "Open V1")

    def test_abort_closes_all_valves(self):
        hal = make_hal()
        engine = RecipeEngine(hal)
        engine.load(SIMPLE_RECIPE)
        engine.start()
        time.sleep(0.01)
        engine.abort()
        time.sleep(0.1)  # valve response delay
        for valve in hal.all_valves().values():
            assert valve.is_closed()

    def test_empty_recipe_done_immediately(self):
        engine = RecipeEngine(make_hal())
        engine.load({"steps": []})
        engine.start()
        result = engine.tick()
        assert not result
        assert engine.is_done
