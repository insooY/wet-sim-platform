"""Connected Session — ZMQ 소켓 생성, 핸드셰이크, heartbeat 관리."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from src.broker import topics as T
from src.connected.command_receiver import CommandReceiver
from src.connected.state_reporter import StateReporter
from src.hal.hal_manager import HALManager

log = logging.getLogger(__name__)

_HEARTBEAT_INTERVAL = 1.0   # 초
_HEARTBEAT_TIMEOUT  = 3.0   # 초 — 이 시간 동안 heartbeat 없으면 연결 해제


class ConnectedSession:
    """외부 GUI와의 ZMQ 세션 전체를 관리한다.

    사용법:
        session = ConnectedSession(hal, pub_port=5555, sub_port=5556)
        session.start()          # ZMQ 소켓 열기, CommandReceiver 시작
        # Qt QTimer로 tick() 주기적 호출
        session.stop()           # 세션 종료
    """

    def __init__(
        self,
        hal: HALManager,
        pub_port: int = 5555,
        sub_port: int = 5556,
        host: str = "127.0.0.1",
    ) -> None:
        self._hal = hal
        self._pub_port = pub_port
        self._sub_port = sub_port
        self._host = host

        self._ctx = None
        self._pub_sock = None
        self._sub_sock = None

        self._reporter: StateReporter | None = None
        self._receiver: CommandReceiver | None = None

        self._connected = False
        self._last_heartbeat_rx = 0.0
        self._last_heartbeat_tx = 0.0

        self._message_log: list[dict] = []
        self._on_connect_cb: Callable[[], None] | None = None
        self._on_disconnect_cb: Callable[[], None] | None = None

    # ── 콜백 등록 ─────────────────────────────────────────────────────────────

    def on_connect(self, cb: Callable[[], None]) -> None:
        self._on_connect_cb = cb

    def on_disconnect(self, cb: Callable[[], None]) -> None:
        self._on_disconnect_cb = cb

    @property
    def message_log(self) -> list[dict]:
        return self._message_log

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── 생명주기 ──────────────────────────────────────────────────────────────

    def start(self) -> bool:
        try:
            import zmq
            self._ctx = zmq.Context()

            self._pub_sock = self._ctx.socket(zmq.PUB)
            self._pub_sock.bind(f"tcp://{self._host}:{self._pub_port}")

            self._sub_sock = self._ctx.socket(zmq.SUB)
            self._sub_sock.connect(f"tcp://{self._host}:{self._sub_port}")
            self._sub_sock.setsockopt(zmq.SUBSCRIBE, b"")

            time.sleep(0.05)   # ZMQ 연결 안정화

            self._reporter = StateReporter(self._hal, self._pub_sock)
            self._reporter.set_log_sink(self._message_log)

            self._receiver = CommandReceiver(self._hal, self._sub_sock)
            self._receiver.set_log_sink(self._message_log)
            self._receiver.add_callback(self._on_command)
            self._receiver.start()

            log.info("ConnectedSession 시작: PUB=%d SUB=%d", self._pub_port, self._sub_port)
            return True
        except ImportError:
            log.error("pyzmq가 설치되지 않아 Connected Mode를 사용할 수 없습니다.")
            return False
        except Exception as e:
            log.error("ConnectedSession 시작 오류: %s", e)
            return False

    def stop(self) -> None:
        if self._receiver:
            self._receiver.stop()
        self._connected = False
        if self._pub_sock:
            self._pub_sock.close(linger=0)
        if self._sub_sock:
            self._sub_sock.close(linger=0)
        if self._ctx:
            self._ctx.term()
        self._pub_sock = None
        self._sub_sock = None
        self._ctx = None
        log.info("ConnectedSession 종료")

    # ── tick (Qt QTimer에서 호출) ─────────────────────────────────────────────

    def tick(self) -> None:
        """상태 발행 + heartbeat 처리. Qt 타이머로 주기적 호출."""
        if not self._reporter:
            return

        # 상태 발행
        self._reporter.report()

        now = time.monotonic()

        # heartbeat 송신
        if now - self._last_heartbeat_tx >= _HEARTBEAT_INTERVAL:
            self._send(T.SYSTEM_HEARTBEAT, {"ts": int(time.time() * 1000)})
            self._last_heartbeat_tx = now

        # heartbeat 타임아웃 감지
        if self._connected and self._last_heartbeat_rx > 0:
            if now - self._last_heartbeat_rx > _HEARTBEAT_TIMEOUT:
                log.warning("Heartbeat 타임아웃 — 연결 해제")
                self._connected = False
                if self._on_disconnect_cb:
                    self._on_disconnect_cb()

    # ── 수신 명령 처리 ────────────────────────────────────────────────────────

    def _on_command(self, topic: str, payload: dict[str, Any]) -> None:
        if topic == T.SYSTEM_CONNECT:
            self._handle_connect(payload)
        elif topic == T.SYSTEM_HEARTBEAT:
            self._last_heartbeat_rx = time.monotonic()
        elif topic == T.SYSTEM_DISCONNECT:
            log.info("외부 GUI 연결 해제 요청")
            self._connected = False
            if self._on_disconnect_cb:
                self._on_disconnect_cb()

    def _handle_connect(self, payload: dict[str, Any]) -> None:
        log.info("외부 GUI 접속: %s", payload.get("client", "unknown"))
        self._connected = True
        self._last_heartbeat_rx = time.monotonic()

        # 장비 정보 + I/O 목록 응답
        io_info = {
            "motors":  list(self._hal.all_motors().keys()),
            "valves":  list(self._hal.all_valves().keys()),
            "sensors": list(self._hal.all_sensors().keys()),
            "heaters": list(self._hal.all_heaters().keys()),
        }
        self._send(T.SYSTEM_CONNECTED, {"equipment": "simulator", "io": io_info})

        if self._on_connect_cb:
            self._on_connect_cb()

    def _send(self, topic: str, payload: dict[str, Any]) -> None:
        if not self._pub_sock:
            return
        msg = {"topic": topic, "timestamp": int(time.time() * 1000), "payload": payload}
        try:
            self._pub_sock.send_string(json.dumps(msg), flags=0)
            self._message_log.append({
                "dir": "TX", "ts": msg["timestamp"],
                "topic": topic, "payload": payload,
            })
        except Exception as e:
            log.debug("send 오류: %s", e)

    # ── reporter 접근자 (MainWindow → recipe step 발행용) ─────────────────────

    @property
    def reporter(self) -> StateReporter | None:
        return self._reporter
