"""플러그인 공통 인터페이스."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget
    from src.broker.message_broker import IMessageBroker


class IPlugin(ABC):
    """모든 플러그인이 구현해야 하는 인터페이스."""

    @abstractmethod
    def get_name(self) -> str: ...

    @abstractmethod
    def get_version(self) -> str: ...

    @abstractmethod
    def initialize(self, config: dict[str, Any]) -> bool: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def shutdown(self) -> None: ...

    @abstractmethod
    def set_broker(self, broker: "IMessageBroker") -> None: ...

    @abstractmethod
    def get_publish_topics(self) -> list[str]: ...

    @abstractmethod
    def get_subscribe_topics(self) -> list[str]: ...

    def get_widget(self) -> Optional["QWidget"]:
        """GUI 패널 위젯. 없는 플러그인은 None을 반환한다."""
        return None
