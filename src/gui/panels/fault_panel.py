"""Fault Injection 패널 — Standalone 모드에서 이상 상황을 토글한다."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from src.core.fault_injection import FaultInjector, FaultType
from src.hal.hal_manager import HALManager

if TYPE_CHECKING:
    pass


class FaultPanel(QWidget):
    """Fault Injection 토글 버튼 패널."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._injector: FaultInjector | None = None
        self._active_keys: dict[str, str] = {}   # button_key → fault key
        self._buttons: dict[str, QPushButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        title = QLabel("⚠ Fault Injection")
        title.setStyleSheet("font-weight: bold; color: #ff9800; font-size: 12px;")
        root.addWidget(title)

        self._content = QVBoxLayout()
        self._content.setSpacing(4)

        scroll_widget = QWidget()
        scroll_widget.setLayout(self._content)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_widget)
        root.addWidget(scroll)

    def load_hal(self, hal: HALManager) -> None:
        """HAL을 기반으로 Fault 버튼을 동적 생성한다."""
        self._injector = FaultInjector(hal)
        self._active_keys.clear()
        self._buttons.clear()

        # 기존 위젯 제거
        while self._content.count():
            item = self._content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 센서 Fault
        sensors = list(hal.all_sensors().keys())
        if sensors:
            self._content.addWidget(self._section("센서"))
            for sid in sensors:
                self._add_fault_btn(f"FAIL:{sid}", f"센서 단선 [{sid}]",
                                    FaultType.SENSOR_FAIL, sid)
                self._add_fault_btn(f"DRIFT:{sid}", f"센서 드리프트 [{sid}]",
                                    FaultType.SENSOR_DRIFT, sid,
                                    params={"rate_per_tick": 0.1})

        # 밸브 Fault
        valves = list(hal.all_valves().keys())
        if valves:
            self._content.addWidget(self._section("밸브"))
            for vid in valves:
                self._add_fault_btn(f"STUCK:{vid}", f"밸브 고착 [{vid}]",
                                    FaultType.VALVE_STUCK, vid)

        # 모터 Fault
        motors = list(hal.all_motors().keys())
        if motors:
            self._content.addWidget(self._section("모터"))
            for mid in motors:
                self._add_fault_btn(f"ERR:{mid}", f"모터 에러 [{mid}]",
                                    FaultType.MOTOR_ERROR, mid)

        self._content.addStretch()

    def clear_all(self) -> None:
        if self._injector:
            self._injector.remove_all()
        for key in list(self._active_keys):
            btn = self._buttons.get(key)
            if btn:
                self._set_btn_state(btn, False)
        self._active_keys.clear()

    # ── 내부 ─────────────────────────────────────────────────────────────────

    def _section(self, title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setStyleSheet("color: #888; font-size: 10px; margin-top: 4px;")
        return lbl

    def _add_fault_btn(self, btn_key: str, label: str,
                       fault_type: FaultType, device_id: str,
                       params: dict | None = None) -> None:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setFixedHeight(26)
        self._set_btn_state(btn, False)
        btn.clicked.connect(
            lambda checked, k=btn_key, ft=fault_type, did=device_id, p=params:
            self._toggle(k, ft, did, p or {}, checked)
        )
        self._buttons[btn_key] = btn
        self._content.addWidget(btn)

    def _toggle(self, btn_key: str, fault_type: FaultType,
                device_id: str, params: dict, checked: bool) -> None:
        if not self._injector:
            return
        if checked:
            fault_key = self._injector.inject(fault_type, device_id, params)
            self._active_keys[btn_key] = fault_key
            self._set_btn_state(self._buttons[btn_key], True)
        else:
            fault_key = self._active_keys.pop(btn_key, None)
            if fault_key:
                self._injector.remove(fault_key)
            self._set_btn_state(self._buttons[btn_key], False)

    @staticmethod
    def _set_btn_state(btn: QPushButton, active: bool) -> None:
        if active:
            btn.setStyleSheet(
                "QPushButton { background: #c62828; color: white; border-radius: 3px;"
                " font-size: 11px; } QPushButton:hover { background: #b71c1c; }"
            )
        else:
            btn.setStyleSheet(
                "QPushButton { background: #333; color: #ccc; border-radius: 3px;"
                " border: 1px solid #555; font-size: 11px; }"
                "QPushButton:hover { background: #444; }"
            )
