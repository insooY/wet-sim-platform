from abc import ABC, abstractmethod


class IMotor(ABC):
    """모터 하드웨어 추상화 인터페이스"""

    @abstractmethod
    def move_absolute(self, position: float) -> None: ...

    @abstractmethod
    def move_relative(self, distance: float) -> None: ...

    @abstractmethod
    def set_speed(self, speed: float) -> None: ...

    @abstractmethod
    def get_position(self) -> float: ...

    @abstractmethod
    def is_move_done(self) -> bool: ...

    @abstractmethod
    def is_homed(self) -> bool: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def home(self) -> None: ...

    @abstractmethod
    def emergency_stop(self) -> None: ...


class IValve(ABC):
    """밸브 하드웨어 추상화 인터페이스"""

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def is_open(self) -> bool: ...

    @abstractmethod
    def is_closed(self) -> bool: ...

    @abstractmethod
    def get_response_ms(self) -> int: ...


class ISensor(ABC):
    """센서 하드웨어 추상화 인터페이스"""

    @abstractmethod
    def read(self) -> float: ...

    @abstractmethod
    def get_unit(self) -> str: ...

    @abstractmethod
    def get_range(self) -> tuple[float, float]: ...

    @abstractmethod
    def is_healthy(self) -> bool: ...


class IHeater(ABC):
    """히터 하드웨어 추상화 인터페이스"""

    @abstractmethod
    def set_target(self, temperature: float) -> None: ...

    @abstractmethod
    def get_target(self) -> float: ...

    @abstractmethod
    def get_current(self) -> float: ...

    @abstractmethod
    def enable(self) -> None: ...

    @abstractmethod
    def disable(self) -> None: ...

    @abstractmethod
    def is_at_target(self, tolerance: float = 0.5) -> bool: ...
