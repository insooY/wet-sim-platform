from abc import ABC, abstractmethod

from src.transport.interfaces import ITransport


class IProtocol(ABC):
    """PLC 프로토콜 추상 인터페이스"""

    @abstractmethod
    def set_transport(self, transport: ITransport) -> None: ...

    @abstractmethod
    def connect(self, config: dict) -> bool: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def read_bool(self, address: str) -> bool: ...

    @abstractmethod
    def write_bool(self, address: str, value: bool) -> None: ...

    @abstractmethod
    def read_float(self, address: str) -> float: ...

    @abstractmethod
    def write_float(self, address: str, value: float) -> None: ...

    @abstractmethod
    def read_int(self, address: str) -> int: ...

    @abstractmethod
    def write_int(self, address: str, value: int) -> None: ...
