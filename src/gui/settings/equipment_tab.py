from typing import Any

from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QLabel, QLineEdit, QSpinBox,
    QVBoxLayout, QWidget,
)


class EquipmentTab(QWidget):
    """Settings > Equipment 탭 — 장비 기본 정보 편집."""

    _TYPES = ["batch_spray", "single_spin", "batch_immersion"]
    _WAFER_SIZES = ["150mm", "200mm", "300mm"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        box = QGroupBox("장비 기본 정보")
        form = QFormLayout(box)
        form.setSpacing(10)

        self._name = QLineEdit()
        self._name.setPlaceholderText("예: Batch Spray Cleaner")
        form.addRow("장비 이름", self._name)

        self._eq_type = QComboBox()
        self._eq_type.addItems(self._TYPES)
        form.addRow("장비 타입", self._eq_type)

        self._wafer_size = QComboBox()
        self._wafer_size.addItems(self._WAFER_SIZES)
        form.addRow("웨이퍼 크기", self._wafer_size)

        self._cassette_slots = QSpinBox()
        self._cassette_slots.setRange(1, 50)
        self._cassette_slots.setValue(25)
        form.addRow("카세트 슬롯 수", self._cassette_slots)

        self._loadports = QSpinBox()
        self._loadports.setRange(1, 4)
        self._loadports.setValue(1)
        form.addRow("로드포트 수", self._loadports)

        root.addWidget(box)
        root.addStretch()

        note = QLabel("* 장비 타입을 변경하면 3D 모델과 I/O 구성이 초기화됩니다.")
        note.setStyleSheet("color: #aaa; font-size: 11px;")
        root.addWidget(note)

    # ── public API ───────────────────────────────────────────────────────────

    def load_config(self, cfg: dict[str, Any]) -> None:
        eq = cfg.get("equipment", {})
        self._name.setText(eq.get("name", ""))

        idx = self._eq_type.findText(eq.get("type", "batch_spray"))
        self._eq_type.setCurrentIndex(max(idx, 0))

        idx = self._wafer_size.findText(eq.get("wafer_size", "300mm"))
        self._wafer_size.setCurrentIndex(max(idx, 0))

        self._cassette_slots.setValue(int(eq.get("cassette_slots", 25)))
        self._loadports.setValue(int(eq.get("loadports", 1)))

    def get_config(self) -> dict[str, Any]:
        return {
            "equipment": {
                "name": self._name.text().strip(),
                "type": self._eq_type.currentText(),
                "wafer_size": self._wafer_size.currentText(),
                "cassette_slots": self._cassette_slots.value(),
                "loadports": self._loadports.value(),
            }
        }
