import pytest

from src.transport.simulator_transport import SimulatorTransport


def test_open_close():
    t = SimulatorTransport()
    assert not t.is_connected()
    assert t.open({}) is True
    assert t.is_connected()
    t.close()
    assert not t.is_connected()


def test_send_receive_with_responder():
    t = SimulatorTransport()
    t.open({})
    t.set_responder(lambda data: b"ACK:" + data)

    sent = t.send(b"HELLO")
    assert sent == 5

    response = t.receive(max_len=256, timeout_ms=100)
    assert response == b"ACK:HELLO"


def test_receive_timeout_returns_empty():
    t = SimulatorTransport()
    t.open({})
    result = t.receive(max_len=256, timeout_ms=50)
    assert result == b""


def test_send_when_disconnected_returns_zero():
    t = SimulatorTransport()
    assert t.send(b"DATA") == 0


def test_inject():
    t = SimulatorTransport()
    t.open({})
    t.inject(b"INJECTED")
    result = t.receive(max_len=256, timeout_ms=100)
    assert result == b"INJECTED"


def test_receive_respects_max_len():
    t = SimulatorTransport()
    t.open({})
    t.inject(b"LONGDATA")
    result = t.receive(max_len=4, timeout_ms=100)
    assert result == b"LONG"


def test_close_clears_queue():
    t = SimulatorTransport()
    t.open({})
    t.inject(b"DATA")
    t.close()
    t.open({})
    result = t.receive(max_len=256, timeout_ms=50)
    assert result == b""
