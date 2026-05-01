from typing import Any

from src.transport.interfaces import ITransport
from .interfaces import IProtocol


class SimulatorProtocol(IProtocol):
    """Key-Value 메모리 기반 시뮬레이터 프로토콜 — 실제 통신 없이 주소를 딕셔너리 키로 읽기/쓰기."""

    def __init__(self) -> None:
        self._memory: dict[str, Any] = {}
        self._transport: ITransport | None = None
        self._connected = False

    def set_transport(self, transport: ITransport) -> None:
        self._transport = transport

    def connect(self, config: dict) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def read_bool(self, address: str) -> bool:
        return bool(self._memory.get(address, False))

    def write_bool(self, address: str, value: bool) -> None:
        self._memory[address] = bool(value)

    def read_float(self, address: str) -> float:
        return float(self._memory.get(address, 0.0))

    def write_float(self, address: str, value: float) -> None:
        self._memory[address] = float(value)

    def read_int(self, address: str) -> int:
        return int(self._memory.get(address, 0))

    def write_int(self, address: str, value: int) -> None:
        self._memory[address] = int(value)

    def set_initial_values(self, values: dict[str, Any]) -> None:
        """테스트 또는 초기화 시 메모리에 초깃값을 일괄 주입한다."""
        self._memory.update(values)

    def get_memory(self) -> dict[str, Any]:
        return dict(self._memory)
