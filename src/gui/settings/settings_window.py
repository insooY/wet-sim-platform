from typing import Any

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QMessageBox,
    QTabWidget, QVBoxLayout, QWidget,
)

from src.config.config_loader import ConfigLoader
from src.config.config_writer import ConfigWriter
from src.config.schema import ValidationError, validate_equipment
from src.gui.settings.equipment_tab import EquipmentTab
from src.gui.settings.io_tab import IOTab


class SettingsWindow(QDialog):
    """설정 창 — Equipment / Baths / I/O / Communication / 3D Models / Export 탭."""

    def __init__(self, project_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(860, 560)

        self._project_name = project_name
        self._loader = ConfigLoader()
        self._writer = ConfigWriter()
        self._eq_cfg: dict[str, Any] = {}

        self._build_ui()
        self._load()

    # ── UI 구성 ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._tabs = QTabWidget()

        # ── 구현 완료 탭 ──
        self._eq_tab = EquipmentTab()
        self._tabs.addTab(self._eq_tab, "Equipment")

        self._io_tab = IOTab()
        self._tabs.addTab(self._io_tab, "I/O Devices")

        # ── 준비 중 탭 (Step 4에서 구현) ──
        for label in ("Baths", "Communication", "3D Models", "Export"):
            placeholder = QWidget()
            msg = QLabel(f"{label} 탭은 준비 중입니다.")
            msg.setStyleSheet("color: #888; margin: 24px;")
            from PyQt6.QtWidgets import QHBoxLayout
            pl = QHBoxLayout(placeholder)
            pl.addWidget(msg)
            self._tabs.addTab(placeholder, label)

        layout.addWidget(self._tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    # ── 로드 / 저장 ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            self._eq_cfg = self._loader.load_equipment(self._project_name)
            self._eq_tab.load_config(self._eq_cfg)
            self._io_tab.load_config(self._eq_cfg)
        except Exception as e:
            QMessageBox.warning(self, "로드 오류", f"설정을 불러오지 못했습니다:\n{e}")

    def _save(self) -> None:
        merged = {
            **self._eq_cfg,
            **self._eq_tab.get_config(),
            **self._io_tab.get_config(),
        }

        try:
            validate_equipment(merged)
        except ValidationError as e:
            QMessageBox.warning(self, "검증 오류", str(e))
            return

        try:
            self._writer.save_equipment(self._project_name, merged)
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"파일을 저장하지 못했습니다:\n{e}")
            return

        self.accept()
