"""InprocBroker / IMessageBroker 단위 테스트."""
from __future__ import annotations

import threading
import time

import pytest

from src.broker.message_broker import InprocBroker
from src.broker import topics as T


# ── 픽스처 ───────────────────────────────────────────────────────────────────

@pytest.fixture
def broker() -> InprocBroker:
    b = InprocBroker()
    b.start()
    yield b
    b.stop()


# ── 기본 발행/구독 ────────────────────────────────────────────────────────────

def test_subscribe_receives_matching_topic(broker):
    received = []
    broker.subscribe("sensor/", lambda t, p: received.append((t, p)))
    broker.publish("sensor/S1/value", {"value": 42.0})
    assert len(received) == 1
    assert received[0][0] == "sensor/S1/value"
    assert received[0][1]["value"] == 42.0


def test_subscribe_ignores_non_matching_topic(broker):
    received = []
    broker.subscribe("sensor/", lambda t, p: received.append(t))
    broker.publish("motor/M1/position", {"position": 100.0})
    assert received == []


def test_multiple_subscribers_same_prefix(broker):
    calls_a, calls_b = [], []
    broker.subscribe("alarm/", lambda t, p: calls_a.append(t))
    broker.subscribe("alarm/", lambda t, p: calls_b.append(t))
    broker.publish(T.ALARM_NEW, {"id": "ALM001"})
    assert len(calls_a) == 1
    assert len(calls_b) == 1


def test_multiple_subscribers_different_prefix(broker):
    sensor_calls, motor_calls = [], []
    broker.subscribe("sensor/", lambda t, p: sensor_calls.append(t))
    broker.subscribe("motor/", lambda t, p: motor_calls.append(t))
    broker.publish("sensor/S1/value", {})
    broker.publish("motor/M1/position", {})
    assert len(sensor_calls) == 1
    assert len(motor_calls) == 1


def test_prefix_does_not_match_shorter_topic(broker):
    received = []
    broker.subscribe("sensor/S1/value", lambda t, p: received.append(t))
    broker.publish("sensor/S1", {})          # prefix longer than topic
    assert received == []


def test_exact_topic_match_works(broker):
    received = []
    broker.subscribe("equipment/state", lambda t, p: received.append(t))
    broker.publish("equipment/state", {"state": "RUNNING"})
    assert len(received) == 1


# ── unsubscribe ───────────────────────────────────────────────────────────────

def test_unsubscribe_stops_delivery(broker):
    received = []

    def cb(t, p):
        received.append(t)

    broker.subscribe("sensor/", cb)
    broker.publish("sensor/S1/value", {})
    broker.unsubscribe("sensor/", cb)
    broker.publish("sensor/S1/value", {})
    assert len(received) == 1   # 첫 번째만 수신


def test_unsubscribe_unknown_callback_is_noop(broker):
    broker.subscribe("sensor/", lambda t, p: None)
    broker.unsubscribe("sensor/", lambda t, p: None)   # 다른 람다, 무시


# ── 페이로드 내용 검증 ────────────────────────────────────────────────────────

def test_payload_passed_intact(broker):
    received = []
    broker.subscribe("recipe/", lambda t, p: received.append(p))
    payload = {"step": 3, "name": "DIW Rinse", "flag": True}
    broker.publish(T.RECIPE_STEP, payload)
    assert received[0] == payload


# ── stop 후 콜백 없음 ────────────────────────────────────────────────────────

def test_stop_clears_callbacks(broker):
    received = []
    broker.subscribe("sensor/", lambda t, p: received.append(t))
    broker.stop()
    broker.publish("sensor/S1/value", {})
    assert received == []


# ── 스레드 안전성 ─────────────────────────────────────────────────────────────

def test_concurrent_publish_is_safe(broker):
    received = []
    broker.subscribe("sensor/", lambda t, p: received.append(t))

    def publish_many():
        for _ in range(50):
            broker.publish("sensor/S1/value", {"value": 1.0})

    threads = [threading.Thread(target=publish_many) for _ in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert len(received) == 200


# ── 토픽 헬퍼 ────────────────────────────────────────────────────────────────

def test_topic_helpers_produce_correct_strings():
    assert T.sensor_value("S1") == "sensor/S1/value"
    assert T.motor_position("M1") == "motor/M1/position"
    assert T.motor_status("M1") == "motor/M1/status"
    assert T.valve_state("V3") == "valve/V3/state"
    assert T.heater_temp("H1") == "heater/H1/temperature"


def test_topic_prefix_match_via_broker(broker):
    """sensor_value 헬퍼로 만든 토픽이 'sensor/' 구독에 전달되는지 확인."""
    received = []
    broker.subscribe("sensor/", lambda t, p: received.append(t))
    broker.publish(T.sensor_value("S2"), {"value": 99.9})
    assert received == ["sensor/S2/value"]
