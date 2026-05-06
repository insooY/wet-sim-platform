"""ZeroMQ Pub/Sub 메시지 브로커 래퍼."""
from __future__ import annotations

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Callable

log = logging.getLogger(__name__)

MessageCallback = Callable[[str, dict[str, Any]], None]  # (topic, payload)


# ── 인터페이스 ────────────────────────────────────────────────────────────────

class IMessageBroker(ABC):
    """메시지 브로커 인터페이스."""

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def publish(self, topic: str, payload: dict[str, Any]) -> None: ...

    @abstractmethod
    def subscribe(self, topic_prefix: str, callback: MessageCallback) -> None: ...

    @abstractmethod
    def unsubscribe(self, topic_prefix: str, callback: MessageCallback) -> None: ...


# ── ZeroMQ 구현 ───────────────────────────────────────────────────────────────

class MessageBroker(IMessageBroker):
    """ZeroMQ PUB/SUB 기반 메시지 브로커.

    인스턴스마다 독립적인 PUB 소켓(송신)과 SUB 소켓(수신)을 가진다.
    - 주 프로세스: pub_port=5555, sub_ports=[5556] (플러그인이 5556으로 발행)
    - 플러그인:    pub_port=5556, sub_ports=[5555] (주 프로세스가 5555로 발행)
    """

    def __init__(
        self,
        pub_port: int = 5555,
        sub_ports: list[int] | None = None,
        host: str = "127.0.0.1",
    ) -> None:
        self._pub_port = pub_port
        self._sub_ports = sub_ports or []
        self._host = host
        self._running = False
        self._thread: threading.Thread | None = None
        self._callbacks: dict[str, list[MessageCallback]] = {}
        self._lock = threading.Lock()
        self._ctx = None
        self._pub_sock = None
        self._sub_sock = None

    # ── 생명주기 ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        try:
            import zmq
            self._ctx = zmq.Context()
            self._pub_sock = self._ctx.socket(zmq.PUB)
            self._pub_sock.bind(f"tcp://{self._host}:{self._pub_port}")

            if self._sub_ports:
                self._sub_sock = self._ctx.socket(zmq.SUB)
                for port in self._sub_ports:
                    self._sub_sock.connect(f"tcp://{self._host}:{port}")
                self._sub_sock.setsockopt(zmq.SUBSCRIBE, b"")  # 모든 토픽 수신

            self._running = True
            self._thread = threading.Thread(
                target=self._recv_loop, name="broker-recv", daemon=True
            )
            self._thread.start()
            time.sleep(0.05)   # ZMQ 소켓 연결 안정화
        except ImportError:
            log.warning("pyzmq가 설치되지 않아 MessageBroker가 비활성화됩니다.")
        except Exception as e:
            log.error("MessageBroker start 오류: %s", e)

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._pub_sock:
            self._pub_sock.close(linger=0)
        if self._sub_sock:
            self._sub_sock.close(linger=0)
        if self._ctx:
            self._ctx.term()
        self._pub_sock = None
        self._sub_sock = None
        self._ctx = None

    # ── 발행 / 구독 ───────────────────────────────────────────────────────────

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if not self._pub_sock:
            return
        msg = {
            "topic": topic,
            "timestamp": int(time.time() * 1000),
            "payload": payload,
        }
        try:
            self._pub_sock.send_string(json.dumps(msg), flags=0)
        except Exception as e:
            log.debug("publish 오류 (%s): %s", topic, e)

    def subscribe(self, topic_prefix: str, callback: MessageCallback) -> None:
        with self._lock:
            self._callbacks.setdefault(topic_prefix, []).append(callback)

    def unsubscribe(self, topic_prefix: str, callback: MessageCallback) -> None:
        with self._lock:
            cbs = self._callbacks.get(topic_prefix, [])
            if callback in cbs:
                cbs.remove(callback)

    # ── 수신 루프 (백그라운드 스레드) ────────────────────────────────────────

    def _recv_loop(self) -> None:
        if not self._sub_sock:
            return
        try:
            import zmq
            poller = zmq.Poller()
            poller.register(self._sub_sock, zmq.POLLIN)
            while self._running:
                socks = dict(poller.poll(timeout=100))
                if self._sub_sock in socks:
                    raw = self._sub_sock.recv_string()
                    self._dispatch(raw)
        except Exception as e:
            if self._running:
                log.error("broker recv_loop 오류: %s", e)

    def _dispatch(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        topic: str = msg.get("topic", "")
        payload: dict = msg.get("payload", {})
        with self._lock:
            callbacks = list(self._callbacks.items())
        for prefix, cbs in callbacks:
            if topic.startswith(prefix):
                for cb in cbs:
                    try:
                        cb(topic, payload)
                    except Exception as e:
                        log.error("broker callback 오류 [%s]: %s", topic, e)


# ── 인프로세스 브로커 (테스트 / Standalone 모드용) ───────────────────────────

class InprocBroker(IMessageBroker):
    """ZMQ 없이 동작하는 동일 프로세스 내 이벤트 버스.

    Standalone 모드에서 플러그인이 같은 프로세스에 있을 때 사용한다.
    """

    def __init__(self) -> None:
        self._callbacks: dict[str, list[MessageCallback]] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        pass

    def stop(self) -> None:
        with self._lock:
            self._callbacks.clear()

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        msg_time = int(time.time() * 1000)
        with self._lock:
            callbacks = list(self._callbacks.items())
        for prefix, cbs in callbacks:
            if topic.startswith(prefix):
                for cb in cbs:
                    try:
                        cb(topic, payload)
                    except Exception as e:
                        log.error("InprocBroker callback 오류 [%s]: %s", topic, e)

    def subscribe(self, topic_prefix: str, callback: MessageCallback) -> None:
        with self._lock:
            self._callbacks.setdefault(topic_prefix, []).append(callback)

    def unsubscribe(self, topic_prefix: str, callback: MessageCallback) -> None:
        with self._lock:
            cbs = self._callbacks.get(topic_prefix, [])
            if callback in cbs:
                cbs.remove(callback)
