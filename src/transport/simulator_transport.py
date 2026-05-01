import queue
import time
from typing import Callable

from .interfaces import ITransport


class SimulatorTransport(ITransport):
    """루프백 전송 — 명령을 분석해 가상 응답을 rx 큐에 삽입."""

    def __init__(self) -> None:
        self._connected = False
        self._rx_queue: queue.Queue[bytes] = queue.Queue()
        self._responder: Callable[[bytes], bytes | None] | None = None

    def set_responder(self, fn: Callable[[bytes], bytes | None]) -> None:
        """프로토콜 레이어가 자신의 응답 생성 함수를 주입한다."""
        self._responder = fn

    def open(self, config: dict) -> bool:
        self._connected = True
        return True

    def close(self) -> None:
        self._connected = False
        while not self._rx_queue.empty():
            try:
                self._rx_queue.get_nowait()
            except queue.Empty:
                break

    def send(self, data: bytes) -> int:
        if not self._connected:
            return 0
        if self._responder:
            response = self._responder(data)
            if response is not None:
                self._rx_queue.put(response)
        return len(data)

    def receive(self, max_len: int, timeout_ms: int) -> bytes:
        if not self._connected:
            return b""
        try:
            data = self._rx_queue.get(timeout=timeout_ms / 1000.0)
            return data[:max_len]
        except queue.Empty:
            return b""

    def is_connected(self) -> bool:
        return self._connected

    def inject(self, data: bytes) -> None:
        """테스트용 — 응답 큐에 직접 데이터를 주입한다."""
        self._rx_queue.put(data)
