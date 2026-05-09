"""Command Receiver — 외부 GUI의 ZMQ 명령을 수신하여 HAL을 제어한다."""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable

from src.hal.hal_manager import HALManager

log = logging.getLogger(__name__)

# 수신 명령 콜백: (topic, payload) → None
CommandCallback = Callable[[str, dict[str, Any]], None]


class CommandReceiver:
    """ZMQ SUB 소켓에서 명령을 폴링하여 HAL에 적용한다.

    백그라운드 스레드에서 동작하며, HAL 접근은 GIL로 보호된다.
    """

    def __init__(self, hal: HALManager, sub_socket: Any) -> None:
        self._hal = hal
        self._sub = sub_socket
        self._running = False
        self._thread: threading.Thread | None = None
        self._extra_callbacks: list[CommandCallback] = []
        self._log_sink: list[dict] | None = None

    def set_log_sink(self, sink: list[dict]) -> None:
        self._log_sink = sink

    def add_callback(self, cb: CommandCallback) -> None:
        """HAL 처리 외에 추가 콜백을 등록한다 (세션 핸드셰이크 등)."""
        self._extra_callbacks.append(cb)

    # ── 생명주기 ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running or not self._sub:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop, name="cmd-recv", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    # ── 수신 루프 ─────────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        try:
            import zmq
            poller = zmq.Poller()
            poller.register(self._sub, zmq.POLLIN)
            while self._running:
                socks = dict(poller.poll(timeout=100))
                if self._sub in socks:
                    raw = self._sub.recv_string()
                    self._dispatch(raw)
        except Exception as e:
            if self._running:
                log.error("CommandReceiver 오류: %s", e)

    def _dispatch(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        topic: str   = msg.get("topic", "")
        payload: dict = msg.get("payload", {})
        ts: int      = msg.get("timestamp", int(time.time() * 1000))

        if self._log_sink is not None:
            self._log_sink.append({"dir": "RX", "ts": ts,
                                   "topic": topic, "payload": payload})

        # HAL 명령 처리
        self._handle_hal(topic, payload)

        # 추가 콜백 (세션 핸드셰이크 등)
        for cb in self._extra_callbacks:
            try:
                cb(topic, payload)
            except Exception as e:
                log.error("CommandReceiver callback 오류: %s", e)

    def _handle_hal(self, topic: str, payload: dict[str, Any]) -> None:
        try:
            if topic.startswith("command/valve/"):
                vid    = topic.split("/")[2]
                action = payload.get("action", "")
                valve  = self._hal.all_valves().get(vid)
                if valve:
                    if action == "open":
                        valve.open()
                    elif action == "close":
                        valve.close()

            elif topic.startswith("command/motor/"):
                mid    = topic.split("/")[2]
                action = payload.get("action", "")
                motor  = self._hal.all_motors().get(mid)
                if motor and action == "move":
                    motor.move_absolute(float(payload.get("position", 0)))

            elif topic == "command/heater/setpoint":
                hid  = payload.get("id", "")
                temp = payload.get("temperature")
                heater = self._hal.all_heaters().get(hid)
                if heater and temp is not None:
                    heater.set_target(float(temp))
                    heater.enable()

        except Exception as e:
            log.error("HAL 명령 처리 오류 [%s]: %s", topic, e)
