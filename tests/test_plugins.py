"""플러그인 시스템 단위 테스트 — IPlugin / PluginLoader / AlarmPlugin."""
from __future__ import annotations

from typing import Any

import pytest

from src.broker.message_broker import InprocBroker
from src.broker import topics as T
from src.plugins.plugin_interface import IPlugin
from src.plugins.plugin_loader import PluginLoader
from src.plugins.alarm_manager.alarm_plugin import AlarmPlugin


# ── 테스트용 더미 플러그인 ────────────────────────────────────────────────────

class _OkPlugin(IPlugin):
    def __init__(self):
        self.started = False
        self.stopped = False
        self.broker = None

    def get_name(self) -> str:    return "OkPlugin"
    def get_version(self) -> str: return "0.1"
    def initialize(self, config: dict[str, Any]) -> bool:
        self.init_config = config
        return True
    def start(self) -> None:   self.started = True
    def stop(self) -> None:    self.stopped = True
    def shutdown(self) -> None: pass
    def set_broker(self, broker) -> None: self.broker = broker
    def get_publish_topics(self) -> list[str]: return []
    def get_subscribe_topics(self) -> list[str]: return []


class _FailPlugin(IPlugin):
    def get_name(self) -> str:    return "FailPlugin"
    def get_version(self) -> str: return "0.1"
    def initialize(self, config: dict[str, Any]) -> bool: return False
    def start(self) -> None: pass
    def stop(self) -> None: pass
    def shutdown(self) -> None: pass
    def set_broker(self, broker) -> None: pass
    def get_publish_topics(self) -> list[str]: return []
    def get_subscribe_topics(self) -> list[str]: return []


# ── 픽스처 ───────────────────────────────────────────────────────────────────

@pytest.fixture
def broker():
    b = InprocBroker()
    b.start()
    yield b
    b.stop()


@pytest.fixture
def loader(broker):
    return PluginLoader(broker)


# ── PluginLoader ──────────────────────────────────────────────────────────────

def test_register_ok_plugin(loader):
    p = _OkPlugin()
    assert loader.register(p) is True
    assert loader.get_by_name("OkPlugin") is p


def test_register_fail_plugin_not_added(loader):
    p = _FailPlugin()
    assert loader.register(p) is False
    assert loader.get_by_name("FailPlugin") is None


def test_broker_injected_on_register(broker, loader):
    p = _OkPlugin()
    loader.register(p)
    assert p.broker is broker


def test_config_passed_to_initialize(loader):
    p = _OkPlugin()
    loader.register(p, {"key": "val"})
    assert p.init_config == {"key": "val"}


def test_start_all_calls_start(loader):
    p = _OkPlugin()
    loader.register(p)
    loader.start_all()
    assert p.started is True


def test_stop_all_calls_stop(loader):
    p = _OkPlugin()
    loader.register(p)
    loader.stop_all()
    assert p.stopped is True


def test_shutdown_all_removes_plugins(loader):
    loader.register(_OkPlugin())
    loader.register(_OkPlugin())
    loader.shutdown_all()
    assert loader.get_all() == []


def test_get_all_returns_registered(loader):
    p1, p2 = _OkPlugin(), _OkPlugin()
    p2.get_name = lambda: "OkPlugin2"  # type: ignore[method-assign]
    loader.register(p1)
    loader.register(p2)
    assert len(loader.get_all()) == 2


def test_load_from_config_valid_module(broker):
    loader = PluginLoader(broker)
    loader.load_from_config([{
        "module": "src.plugins.alarm_manager.alarm_plugin",
        "class":  "AlarmPlugin",
        "config": {"alarms": []},
    }])
    assert loader.get_by_name("AlarmPlugin") is not None


def test_load_from_config_bad_module_skipped(loader):
    loader.load_from_config([{
        "module": "no.such.module",
        "class":  "Foo",
    }])
    assert loader.get_all() == []


def test_load_from_config_missing_fields_skipped(loader):
    loader.load_from_config([{"config": {}}])   # module/class 없음
    assert loader.get_all() == []


# ── AlarmPlugin ───────────────────────────────────────────────────────────────

@pytest.fixture
def alarm_plugin(broker):
    p = AlarmPlugin()
    p.set_broker(broker)
    p.initialize({
        "alarms": [
            {"id": "ALM001", "sensor": "S1", "condition": "> 80",
             "severity": "critical", "interlock": True},
            {"id": "ALM002", "sensor": "S2", "condition": "< 2.0",
             "severity": "warning",  "interlock": False},
        ]
    })
    p.start()
    yield p
    p.stop()


def test_alarm_fires_when_condition_met(broker, alarm_plugin):
    fired = []
    broker.subscribe(T.ALARM_NEW, lambda t, p: fired.append(p))
    broker.publish(T.sensor_value("S1"), {"value": 85.0})
    assert len(fired) == 1
    assert fired[0]["id"] == "ALM001"


def test_alarm_not_fired_below_threshold(broker, alarm_plugin):
    fired = []
    broker.subscribe(T.ALARM_NEW, lambda t, p: fired.append(p))
    broker.publish(T.sensor_value("S1"), {"value": 75.0})
    assert fired == []


def test_alarm_clears_when_condition_no_longer_met(broker, alarm_plugin):
    cleared = []
    broker.subscribe(T.ALARM_CLEAR, lambda t, p: cleared.append(p))
    # 발생
    broker.publish(T.sensor_value("S1"), {"value": 90.0})
    # 해제
    broker.publish(T.sensor_value("S1"), {"value": 70.0})
    assert len(cleared) == 1
    assert cleared[0]["id"] == "ALM001"


def test_alarm_not_fired_twice_consecutively(broker, alarm_plugin):
    fired = []
    broker.subscribe(T.ALARM_NEW, lambda t, p: fired.append(p))
    broker.publish(T.sensor_value("S1"), {"value": 90.0})
    broker.publish(T.sensor_value("S1"), {"value": 95.0})
    assert len(fired) == 1   # 두 번째 publish는 이미 active 상태


def test_interlock_triggered_with_interlock_true(broker, alarm_plugin):
    interlocks = []
    broker.subscribe(T.INTERLOCK_TRIGGER, lambda t, p: interlocks.append(p))
    broker.publish(T.sensor_value("S1"), {"value": 99.0})
    assert len(interlocks) == 1
    assert interlocks[0]["alarm_id"] == "ALM001"


def test_interlock_not_triggered_with_interlock_false(broker, alarm_plugin):
    interlocks = []
    broker.subscribe(T.INTERLOCK_TRIGGER, lambda t, p: interlocks.append(p))
    broker.publish(T.sensor_value("S2"), {"value": 1.0})   # ALM002, interlock=False
    assert interlocks == []


def test_alarm_less_than_condition(broker, alarm_plugin):
    fired = []
    broker.subscribe(T.ALARM_NEW, lambda t, p: fired.append(p))
    broker.publish(T.sensor_value("S2"), {"value": 1.5})
    assert len(fired) == 1
    assert fired[0]["id"] == "ALM002"


def test_alarm_unrelated_sensor_ignored(broker, alarm_plugin):
    fired = []
    broker.subscribe(T.ALARM_NEW, lambda t, p: fired.append(p))
    broker.publish(T.sensor_value("S99"), {"value": 999.0})
    assert fired == []


def test_alarm_severity_in_payload(broker, alarm_plugin):
    fired = []
    broker.subscribe(T.ALARM_NEW, lambda t, p: fired.append(p))
    broker.publish(T.sensor_value("S1"), {"value": 85.0})
    assert fired[0]["severity"] == "critical"


def test_alarm_condition_operators():
    """AlarmPlugin._evaluate 조건 연산자 전체 검증."""
    p = AlarmPlugin()
    p.set_broker(InprocBroker())
    p.initialize({"alarms": []})
    assert p._evaluate("> 10", 11) is True
    assert p._evaluate("> 10", 10) is False
    assert p._evaluate(">= 10", 10) is True
    assert p._evaluate("< 5", 4) is True
    assert p._evaluate("<= 5", 5) is True
    assert p._evaluate("== 3.5", 3.5) is True
    assert p._evaluate("!= 0", 1) is True
    assert p._evaluate("!= 0", 0) is False
    assert p._evaluate("invalid", 1) is False
