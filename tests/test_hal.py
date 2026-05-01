import math
import time

import pytest

from src.hal.hal_manager import HALManager
from src.hal.simulator_hal import SimHeater, SimMotor, SimSensor, SimValve


# ── SimMotor ──────────────────────────────────────────────────────────────────

class TestSimMotor:
    def test_home_sets_position_zero(self):
        m = SimMotor("M1")
        m.move_absolute(500.0)
        m.home()
        assert m.get_position() == pytest.approx(0.0)
        assert m.is_homed()

    def test_move_absolute_reaches_target(self):
        m = SimMotor("M1", max_speed=1000.0, accel=5000.0)
        m.move_absolute(100.0)
        deadline = time.monotonic() + 2.0
        while not m.is_move_done():
            assert time.monotonic() < deadline, "Motor did not finish in time"
        assert m.get_position() == pytest.approx(100.0, abs=0.1)

    def test_clamps_to_range(self):
        m = SimMotor("M1", max_speed=2000.0, accel=10000.0, position_range=(0.0, 100.0))
        m.move_absolute(999.0)
        deadline = time.monotonic() + 3.0
        while not m.is_move_done():
            assert time.monotonic() < deadline, "Motor did not finish in time"
        assert m.get_position() <= 100.0

    def test_stop_during_move(self):
        m = SimMotor("M1", max_speed=10.0, accel=5.0)
        m.move_absolute(500.0)
        time.sleep(0.05)
        m.stop()
        assert m.is_move_done()

    def test_emergency_stop(self):
        m = SimMotor("M1")
        m.move_absolute(300.0)
        m.emergency_stop()
        assert m.is_move_done()


# ── SimValve ──────────────────────────────────────────────────────────────────

class TestSimValve:
    def test_initial_state_closed(self):
        v = SimValve("V1")
        assert v.is_closed()
        assert not v.is_open()

    def test_open_after_response_delay(self):
        v = SimValve("V1", response_ms=100)
        v.open()
        assert v.is_closed()          # 아직 지연 중
        time.sleep(0.15)
        assert v.is_open()

    def test_close_after_response_delay(self):
        v = SimValve("V1", response_ms=100)
        v.open()
        time.sleep(0.15)
        v.close()
        assert v.is_open()            # 아직 지연 중
        time.sleep(0.15)
        assert v.is_closed()

    def test_get_response_ms(self):
        v = SimValve("V1", response_ms=300)
        assert v.get_response_ms() == 300


# ── SimSensor ─────────────────────────────────────────────────────────────────

class TestSimSensor:
    def test_initial_read_near_initial_value(self):
        s = SimSensor("S1", initial_value=50.0, noise_std=0.0, tau=1.0)
        assert s.read() == pytest.approx(50.0, abs=0.5)

    def test_converges_toward_target(self):
        s = SimSensor("S1", initial_value=0.0, noise_std=0.0, tau=1.0)
        s.set_target(100.0)
        time.sleep(0.5)
        assert s.read() > 30.0        # 1차 지연 — 0.5 tau 이후 약 39% 수렴

    def test_fault_returns_nan(self):
        s = SimSensor("S1")
        s.set_fault(True)
        assert math.isnan(s.read())
        assert not s.is_healthy()

    def test_healthy_by_default(self):
        s = SimSensor("S1")
        assert s.is_healthy()

    def test_unit_and_range(self):
        s = SimSensor("S1", unit="°C", sensor_range=(15.0, 85.0))
        assert s.get_unit() == "°C"
        assert s.get_range() == (15.0, 85.0)


# ── SimHeater ─────────────────────────────────────────────────────────────────

class TestSimHeater:
    def test_initial_temperature_near_ambient(self):
        h = SimHeater("H1")
        assert h.get_current() == pytest.approx(25.0, abs=1.0)

    def test_heats_toward_target_when_enabled(self):
        h = SimHeater("H1", tau=1.0)
        h.set_target(70.0)
        h.enable()
        time.sleep(0.5)
        assert h.get_current() > 25.0

    def test_not_at_target_initially(self):
        h = SimHeater("H1")
        h.set_target(70.0)
        h.enable()
        assert not h.is_at_target(tolerance=1.0)

    def test_get_set_target(self):
        h = SimHeater("H1")
        h.set_target(65.0)
        assert h.get_target() == 65.0


# ── HALManager ────────────────────────────────────────────────────────────────

class TestHALManager:
    EQUIPMENT_CFG = {
        "motors":  [{"id": "M1", "max_speed": 100.0, "accel": 50.0, "range": [0, 500]}],
        "valves":  [{"id": "V1", "response_ms": 200}],
        "sensors": [{"id": "S1", "unit": "°C", "range": [15, 85],
                     "simulation": {"noise": 0.1, "response_tau": 5.0}}],
        "heaters": [{"id": "H1", "power_kw": 5.0, "tau": 30.0}],
    }

    def test_load_creates_instances(self):
        hal = HALManager()
        hal.load_from_config(self.EQUIPMENT_CFG)
        assert "M1" in hal.all_motors()
        assert "V1" in hal.all_valves()
        assert "S1" in hal.all_sensors()
        assert "H1" in hal.all_heaters()

    def test_get_motor_by_id(self):
        hal = HALManager()
        hal.load_from_config(self.EQUIPMENT_CFG)
        m = hal.get_motor("M1")
        assert m is not None

    def test_missing_id_raises(self):
        hal = HALManager()
        hal.load_from_config(self.EQUIPMENT_CFG)
        with pytest.raises(KeyError):
            hal.get_motor("NONEXISTENT")
