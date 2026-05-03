"""Settings > Communication 탭 — PLC/Transport/Robot 통신 설정."""
from typing import Any

from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QVBoxLayout, QWidget,
)


class CommTab(QWidget):
    """Settings > Communication 탭."""

    _PLC_TYPES = ["none", "siemens_s7", "mitsubishi_mc", "beckhoff_ads", "modbus"]
    _TRANSPORT_TYPES = ["tcp", "serial", "ethercat", "simulator"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # ── PLC (메인) ──────────────────────────────────────────────────────
        plc_box = QGroupBox("PLC 메인 컨트롤러")
        plc_form = QFormLayout(plc_box)
        plc_form.setSpacing(10)

        self._plc_type = QComboBox()
        self._plc_type.addItems(self._PLC_TYPES)
        self._plc_type.currentTextChanged.connect(self._on_plc_type_changed)
        plc_form.addRow("PLC 타입", self._plc_type)

        self._plc_transport = QComboBox()
        self._plc_transport.addItems(self._TRANSPORT_TYPES)
        self._plc_transport.currentTextChanged.connect(self._on_plc_transport_changed)
        plc_form.addRow("Transport", self._plc_transport)

        self._plc_ip = QLineEdit()
        self._plc_ip.setPlaceholderText("예: 192.168.1.10")
        plc_form.addRow("IP 주소", self._plc_ip)

        self._plc_port = QSpinBox()
        self._plc_port.setRange(1, 65535)
        self._plc_port.setValue(102)
        plc_form.addRow("포트", self._plc_port)

        self._plc_com = QLineEdit()
        self._plc_com.setPlaceholderText("예: COM3")
        plc_form.addRow("COM 포트", self._plc_com)

        self._plc_baud = QSpinBox()
        self._plc_baud.setRange(1200, 921600)
        self._plc_baud.setValue(9600)
        plc_form.addRow("Baudrate", self._plc_baud)

        self._plc_rack = QSpinBox()
        self._plc_rack.setRange(0, 15)
        plc_form.addRow("Rack (S7)", self._plc_rack)

        self._plc_slot = QSpinBox()
        self._plc_slot.setRange(0, 15)
        self._plc_slot.setValue(1)
        plc_form.addRow("Slot (S7)", self._plc_slot)

        root.addWidget(plc_box)

        # ── 로봇 컨트롤러 ────────────────────────────────────────────────────
        robot_box = QGroupBox("로봇 컨트롤러")
        robot_form = QFormLayout(robot_box)
        robot_form.setSpacing(10)

        self._robot_transport = QComboBox()
        self._robot_transport.addItems(self._TRANSPORT_TYPES)
        self._robot_transport.currentTextChanged.connect(self._on_robot_transport_changed)
        robot_form.addRow("Transport", self._robot_transport)

        self._robot_ip = QLineEdit()
        self._robot_ip.setPlaceholderText("예: 192.168.1.20")
        robot_form.addRow("IP 주소", self._robot_ip)

        self._robot_port = QSpinBox()
        self._robot_port.setRange(1, 65535)
        self._robot_port.setValue(5000)
        robot_form.addRow("포트", self._robot_port)

        self._robot_com = QLineEdit()
        self._robot_com.setPlaceholderText("예: COM4")
        robot_form.addRow("COM 포트", self._robot_com)

        self._robot_baud = QSpinBox()
        self._robot_baud.setRange(1200, 921600)
        self._robot_baud.setValue(9600)
        robot_form.addRow("Baudrate", self._robot_baud)

        root.addWidget(robot_box)
        root.addStretch()

        note = QLabel("* simulator 타입 선택 시 실제 통신 없이 시뮬레이터 모드로 동작합니다.")
        note.setStyleSheet("color: #aaa; font-size: 11px;")
        root.addWidget(note)

        self._on_plc_type_changed(self._plc_type.currentText())
        self._on_plc_transport_changed(self._plc_transport.currentText())
        self._on_robot_transport_changed(self._robot_transport.currentText())

    # ── 동적 필드 표시 ────────────────────────────────────────────────────────

    def _on_plc_type_changed(self, text: str) -> None:
        is_s7 = text == "siemens_s7"
        _set_row_visible(self._plc_rack.parent(), self._plc_rack, is_s7)
        _set_row_visible(self._plc_slot.parent(), self._plc_slot, is_s7)

    def _on_plc_transport_changed(self, text: str) -> None:
        is_tcp = text == "tcp"
        is_serial = text == "serial"
        _set_row_visible(self._plc_ip.parent(), self._plc_ip, is_tcp)
        _set_row_visible(self._plc_port.parent(), self._plc_port, is_tcp)
        _set_row_visible(self._plc_com.parent(), self._plc_com, is_serial)
        _set_row_visible(self._plc_baud.parent(), self._plc_baud, is_serial)

    def _on_robot_transport_changed(self, text: str) -> None:
        is_tcp = text == "tcp"
        is_serial = text == "serial"
        _set_row_visible(self._robot_ip.parent(), self._robot_ip, is_tcp)
        _set_row_visible(self._robot_port.parent(), self._robot_port, is_tcp)
        _set_row_visible(self._robot_com.parent(), self._robot_com, is_serial)
        _set_row_visible(self._robot_baud.parent(), self._robot_baud, is_serial)

    # ── public API ───────────────────────────────────────────────────────────

    def load_config(self, cfg: dict[str, Any]) -> None:
        comm = cfg.get("communication", {})

        plc = comm.get("plc_main", {})
        t = plc.get("transport", {})
        p = plc.get("protocol", {})

        _set_combo(self._plc_type, p.get("type", "simulator"))
        _set_combo(self._plc_transport, t.get("type", "simulator"))
        self._plc_ip.setText(str(t.get("ip", "")))
        self._plc_port.setValue(int(t.get("port", 102)))
        self._plc_com.setText(str(t.get("port", "")))
        self._plc_baud.setValue(int(t.get("baudrate", 9600)))
        self._plc_rack.setValue(int(p.get("rack", 0)))
        self._plc_slot.setValue(int(p.get("slot", 1)))

        robot = comm.get("robot_controller", {})
        rt = robot.get("transport", {})
        _set_combo(self._robot_transport, rt.get("type", "simulator"))
        self._robot_ip.setText(str(rt.get("ip", "")))
        self._robot_port.setValue(int(rt.get("port", 5000)))
        self._robot_com.setText(str(rt.get("port", "")))
        self._robot_baud.setValue(int(rt.get("baudrate", 9600)))

    def get_config(self) -> dict[str, Any]:
        plc_t = self._plc_transport.currentText()
        plc_p = self._plc_type.currentText()

        plc_transport: dict[str, Any] = {"type": plc_t}
        if plc_t == "tcp":
            plc_transport["ip"] = self._plc_ip.text().strip()
            plc_transport["port"] = self._plc_port.value()
        elif plc_t == "serial":
            plc_transport["port"] = self._plc_com.text().strip()
            plc_transport["baudrate"] = self._plc_baud.value()

        plc_protocol: dict[str, Any] = {"type": plc_p}
        if plc_p == "siemens_s7":
            plc_protocol["rack"] = self._plc_rack.value()
            plc_protocol["slot"] = self._plc_slot.value()

        robot_t = self._robot_transport.currentText()
        robot_transport: dict[str, Any] = {"type": robot_t}
        if robot_t == "tcp":
            robot_transport["ip"] = self._robot_ip.text().strip()
            robot_transport["port"] = self._robot_port.value()
        elif robot_t == "serial":
            robot_transport["port"] = self._robot_com.text().strip()
            robot_transport["baudrate"] = self._robot_baud.value()

        return {
            "communication": {
                "plc_main": {
                    "transport": plc_transport,
                    "protocol": plc_protocol,
                },
                "robot_controller": {
                    "transport": robot_transport,
                    "protocol": {"type": "custom_robot"},
                },
            }
        }


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _set_combo(combo: QComboBox, text: str) -> None:
    idx = combo.findText(text)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def _set_row_visible(form_widget: QWidget | None, field: QWidget, visible: bool) -> None:
    """QFormLayout 행의 위젯과 레이블을 함께 표시/숨긴다."""
    if form_widget is None:
        return
    layout = form_widget.layout()
    if not isinstance(layout, QFormLayout):
        return
    row, _ = layout.getWidgetPosition(field)
    if row < 0:
        return
    label_item = layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
    field_item = layout.itemAt(row, QFormLayout.ItemRole.FieldRole)
    if label_item and label_item.widget():
        label_item.widget().setVisible(visible)
    if field_item and field_item.widget():
        field_item.widget().setVisible(visible)
