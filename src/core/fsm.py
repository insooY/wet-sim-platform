from enum import Enum, auto
from typing import Callable


class EquipmentState(Enum):
    IDLE = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    ABORTING = auto()
    ERROR = auto()


_TRANSITIONS: dict[EquipmentState, set[EquipmentState]] = {
    EquipmentState.IDLE:         {EquipmentState.INITIALIZING},
    EquipmentState.INITIALIZING: {EquipmentState.READY, EquipmentState.ERROR},
    EquipmentState.READY:        {EquipmentState.RUNNING, EquipmentState.IDLE},
    EquipmentState.RUNNING:      {EquipmentState.PAUSED, EquipmentState.ABORTING, EquipmentState.IDLE, EquipmentState.ERROR},
    EquipmentState.PAUSED:       {EquipmentState.RUNNING, EquipmentState.ABORTING},
    EquipmentState.ABORTING:     {EquipmentState.IDLE},
    EquipmentState.ERROR:        {EquipmentState.IDLE},
}


class EquipmentFSM:
    """장비 상태 머신 — 허용된 전이만 수행하고 콜백을 호출한다."""

    def __init__(self) -> None:
        self._state = EquipmentState.IDLE
        self._listeners: list[Callable[[EquipmentState, EquipmentState], None]] = []

    @property
    def state(self) -> EquipmentState:
        return self._state

    def add_listener(self, fn: Callable[[EquipmentState, EquipmentState], None]) -> None:
        """상태 전이 시 fn(old_state, new_state) 호출."""
        self._listeners.append(fn)

    def transition(self, new_state: EquipmentState) -> bool:
        allowed = _TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            return False
        old = self._state
        self._state = new_state
        for fn in self._listeners:
            fn(old, new_state)
        return True

    def force(self, new_state: EquipmentState) -> None:
        """비상 정지 등 — 전이 규칙 무시."""
        old = self._state
        self._state = new_state
        for fn in self._listeners:
            fn(old, new_state)

    def is_running(self) -> bool:
        return self._state == EquipmentState.RUNNING

    def is_ready(self) -> bool:
        return self._state == EquipmentState.READY
