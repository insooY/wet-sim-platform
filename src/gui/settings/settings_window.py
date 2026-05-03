from typing import Any

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QMessageBox,
    QTabWidget, QVBoxLayout, QWidget,
)

from src.config.config_loader import ConfigLoader
from src.config.config_writer import ConfigWriter
from src.config.schema import ValidationError, validate_equipment
from src.gui.settings.bath_tab import BathTab
from src.gui.settings.comm_tab import CommTab
from src.gui.settings.equipment_tab import EquipmentTab
from src.gui.settings.export_tab import ExportTab
from src.gui.settings.io_tab import IOTab
from src.gui.settings.models_tab import ModelsTab


class SettingsWindow(QDialog):
    """설정 창 — Equipment / Baths / I/O / Communication / 3D Models / Export 탭."""

    def __init__(self, project_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(860, 600)

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

        self._eq_tab = EquipmentTab()
        self._tabs.addTab(self._eq_tab, "Equipment")

        self._bath_tab = BathTab()
        self._tabs.addTab(self._bath_tab, "Baths")

        self._io_tab = IOTab()
        self._tabs.addTab(self._io_tab, "I/O Devices")

        self._comm_tab = CommTab()
        self._tabs.addTab(self._comm_tab, "Communication")

        self._models_tab = ModelsTab()
        self._tabs.addTab(self._models_tab, "3D Models")

        self._export_tab = ExportTab()
        self._export_tab.set_refresh_callback(self._build_merged)
        self._tabs.addTab(self._export_tab, "Export")

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
            self._bath_tab.load_config(self._eq_cfg)
            self._io_tab.load_config(self._eq_cfg)
            self._comm_tab.load_config(self._eq_cfg)
            self._models_tab.load_config(self._eq_cfg)
            self._export_tab.load_config(self._eq_cfg)
        except Exception as e:
            QMessageBox.warning(self, "로드 오류", f"설정을 불러오지 못했습니다:\n{e}")

    def _build_merged(self) -> dict[str, Any]:
        return {
            **self._eq_cfg,
            **self._eq_tab.get_config(),
            **self._bath_tab.get_config(),
            **self._io_tab.get_config(),
            **self._comm_tab.get_config(),
            **self._models_tab.get_config(),
        }

    def _save(self) -> None:
        merged = self._build_merged()

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
