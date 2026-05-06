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

    def test_motor_move_absolute_executed(self):
        hal = make_hal()
        engine = RecipeEngine(hal)
        engine.load({"steps": [
            {"name": "Move", "motor_moves": [{"id": "M1", "position": 200.0}], "duration": 0},
        ]})
        engine.start()
        deadline = time.monotonic() + 3.0
        while not engine.is_done:
            engine.tick()
            assert time.monotonic() < deadline
        assert hal.get_motor("M1").get_position() == pytest.approx(200.0, abs=1.0)

    def test_step_waits_for_motor_done(self):
        hal = HALManager()
        hal.load_from_config({
            "motors":  [{"id": "M1", "max_speed": 10.0, "accel": 5.0, "range": [0, 500]}],
            "valves":  [],
            "sensors": [],
            "heaters": [],
        })
        engine = RecipeEngine(hal)
        engine.load({"steps": [
            {"name": "SlowMove", "motor_moves": [{"id": "M1", "position": 100.0}], "duration": 0},
            {"name": "Next",     "duration": 0},
        ]})
        engine.start()
        # 느린 모터 — 첫 tick에서 스텝이 넘어가면 안 된다
        engine.tick()
        assert engine.current_step_index == 0

    def test_heater_setpoint_applied(self):
        hal = make_hal()
        engine = RecipeEngine(hal)
        engine.load({"steps": [
            {"name": "Heat", "heater_setpoints": [{"id": "H1", "temperature": 70.0}], "duration": 0},
        ]})
        engine.start()
        engine.tick()
        assert hal.get_heater("H1").get_target() == pytest.approx(70.0)

    def test_wait_heater_blocks_until_reached(self):
        hal = HALManager()
        hal.load_from_config({
            "motors":  [],
            "valves":  [],
            "sensors": [],
            "heaters": [{"id": "H1", "power_kw": 0.001, "tau": 9999.0}],
        })
        engine = RecipeEngine(hal)
        engine.load({"steps": [
            {"name": "Heat",
             "heater_setpoints": [{"id": "H1", "temperature": 80.0}],
             "wait_heater": [{"id": "H1", "tolerance": 1.0}],
             "duration": 0},
            {"name": "Next", "duration": 0},
        ]})
        engine.start()
        engine.tick()
        # 히터가 목표에 도달하지 못했으므로 스텝이 넘어가면 안 된다
        assert engine.current_step_index == 0

    def test_abort_tick_returns_false(self):
        engine = RecipeEngine(make_hal())
        engine.load(SIMPLE_RECIPE)
        engine.start()
        engine.abort()
        assert engine.tick() is False

    def test_abort_is_not_done(self):
        engine = RecipeEngine(make_hal())
        engine.load(SIMPLE_RECIPE)
        engine.start()
        engine.abort()
        assert not engine.is_done

    def test_tick_before_start_returns_false(self):
        engine = RecipeEngine(make_hal())
        engine.load(SIMPLE_RECIPE)
        assert engine.tick() is False

    def test_step_name_fallback_when_no_name_key(self):
        engine = RecipeEngine(make_hal())
        engine.load({"steps": [{"duration": 0}]})
        engine.start()
        assert "Step 0" in engine.current_step_name

    def test_step_callback_order(self):
        engine = RecipeEngine(make_hal())
        order: list[tuple[int, str]] = []
        engine.set_step_callback(lambda i, n: order.append((i, n)))
        engine.load({"steps": [
            {"name": "A", "duration": 0},
            {"name": "B", "duration": 0},
            {"name": "C", "duration": 0},
        ]})
        engine.start()
        deadline = time.monotonic() + 3.0
        while not engine.is_done:
            engine.tick()
            assert time.monotonic() < deadline
        assert order == [(0, "A"), (1, "B"), (2, "C")]

    def test_load_resets_state(self):
        engine = RecipeEngine(make_hal())
        engine.load({"steps": [{"name": "S", "duration": 0}]})
        engine.start()
        deadline = time.monotonic() + 2.0
        while not engine.is_done:
            engine.tick()
            assert time.monotonic() < deadline
        # 다시 load하면 초기 상태로 돌아와야 한다
        engine.load(SIMPLE_RECIPE)
        assert engine.current_step_index == 0
        assert not engine.is_done
