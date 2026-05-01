from abc import ABC, abstractmethod


class ITransport(ABC):
    """물리 전송 계층 추상 인터페이스"""

    @abstractmethod
    def open(self, config: dict) -> bool: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def send(self, data: bytes) -> int: ...

    @abstractmethod
    def receive(self, max_len: int, timeout_ms: int) -> bytes: ...

    @abstractmethod
    def is_connected(self) -> bool: ...
