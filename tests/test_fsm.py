import pytest

from src.core.fsm import EquipmentFSM, EquipmentState


class TestEquipmentFSM:
    def test_initial_state_is_idle(self):
        fsm = EquipmentFSM()
        assert fsm.state == EquipmentState.IDLE

    def test_valid_transition_succeeds(self):
        fsm = EquipmentFSM()
        assert fsm.transition(EquipmentState.INITIALIZING) is True
        assert fsm.state == EquipmentState.INITIALIZING

    def test_invalid_transition_blocked(self):
        fsm = EquipmentFSM()
        # IDLE → RUNNING 은 허용되지 않음
        assert fsm.transition(EquipmentState.RUNNING) is False
        assert fsm.state == EquipmentState.IDLE

    def test_full_happy_path(self):
        fsm = EquipmentFSM()
        assert fsm.transition(EquipmentState.INITIALIZING)
        assert fsm.transition(EquipmentState.READY)
        assert fsm.transition(EquipmentState.RUNNING)
        assert fsm.transition(EquipmentState.IDLE)
        assert fsm.state == EquipmentState.IDLE

    def test_pause_and_resume(self):
        fsm = EquipmentFSM()
        fsm.transition(EquipmentState.INITIALIZING)
        fsm.transition(EquipmentState.READY)
        fsm.transition(EquipmentState.RUNNING)
        assert fsm.transition(EquipmentState.PAUSED)
        assert fsm.transition(EquipmentState.RUNNING)

    def test_abort_from_running(self):
        fsm = EquipmentFSM()
        fsm.transition(EquipmentState.INITIALIZING)
        fsm.transition(EquipmentState.READY)
        fsm.transition(EquipmentState.RUNNING)
        assert fsm.transition(EquipmentState.ABORTING)
        assert fsm.transition(EquipmentState.IDLE)

    def test_error_from_running(self):
        fsm = EquipmentFSM()
        fsm.transition(EquipmentState.INITIALIZING)
        fsm.transition(EquipmentState.READY)
        fsm.transition(EquipmentState.RUNNING)
        assert fsm.transition(EquipmentState.ERROR)
        assert fsm.transition(EquipmentState.IDLE)

    def test_listener_called_on_transition(self):
        fsm = EquipmentFSM()
        events: list[tuple[EquipmentState, EquipmentState]] = []
        fsm.add_listener(lambda old, new: events.append((old, new)))

        fsm.transition(EquipmentState.INITIALIZING)
        assert events == [(EquipmentState.IDLE, EquipmentState.INITIALIZING)]

    def test_listener_not_called_on_blocked_transition(self):
        fsm = EquipmentFSM()
        events: list = []
        fsm.add_listener(lambda old, new: events.append((old, new)))

        fsm.transition(EquipmentState.RUNNING)  # 차단됨
        assert events == []

    def test_force_bypasses_rules(self):
        fsm = EquipmentFSM()
        fsm.force(EquipmentState.RUNNING)  # IDLE → RUNNING 강제
        assert fsm.state == EquipmentState.RUNNING

    def test_is_running_and_is_ready(self):
        fsm = EquipmentFSM()
        assert not fsm.is_running()
        assert not fsm.is_ready()
        fsm.transition(EquipmentState.INITIALIZING)
        fsm.transition(EquipmentState.READY)
        assert fsm.is_ready()
        fsm.transition(EquipmentState.RUNNING)
        assert fsm.is_running()
