"""장비 / 운전 모드 선택 런처 화면."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

_PROJECTS_DIR = Path(__file__).resolve().parents[2] / "config" / "projects"

_EQUIPMENT_ICONS = {
    "batch_spray":     "💦",
    "single_spin":     "🌀",
    "batch_immersion": "🛁",
}

_MODE_DESCRIPTIONS = {
    "standalone": "자체 시뮬레이션 엔진으로 공정을 자동 실행합니다.\n외부 연결 없이 독립 실행됩니다.",
    "connected":  "ZeroMQ로 외부 GUI 제어 프로그램과 연결합니다.\n명령을 수신하여 시뮬레이터가 응답합니다.",
}


class SelectionScreen(QWidget):
    """장비 타입과 운전 모드를 선택하는 런처 화면."""

    sig_launch = pyqtSignal(str, str)  # (project_name, mode)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Wet Process Simulator — 프로젝트 선택")
        self.setMinimumSize(700, 480)
        self._projects: list[dict[str, Any]] = []
        self._selected_project: str = ""
        self._build_ui()
        self._load_projects()

    # ── UI 구성 ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(24)

        # 타이틀
        title = QLabel("Wet Process Simulator")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #e0e0e0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel("시뮬레이션할 장비와 운전 모드를 선택하세요.")
        subtitle.setStyleSheet("font-size: 13px; color: #aaa;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(subtitle)

        # 장비 선택 카드 그리드
        eq_box = QGroupBox("장비 선택")
        self._eq_grid = QGridLayout(eq_box)
        self._eq_grid.setSpacing(12)
        root.addWidget(eq_box)

        # 운전 모드 선택
        mode_box = QGroupBox("운전 모드")
        mode_layout = QHBoxLayout(mode_box)
        mode_layout.setSpacing(16)

        self._mode_group = QButtonGroup(self)
        for mode, desc in _MODE_DESCRIPTIONS.items():
            rb = QRadioButton(mode.capitalize())
            rb.setProperty("mode", mode)
            self._mode_group.addButton(rb)
            mode_cell = QVBoxLayout()
            mode_cell.addWidget(rb)
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #999; font-size: 11px; margin-left: 20px;")
            mode_cell.addWidget(desc_label)
            mode_layout.addLayout(mode_cell)

        # 기본값: standalone
        for btn in self._mode_group.buttons():
            if btn.property("mode") == "standalone":
                btn.setChecked(True)
                break

        root.addWidget(mode_box)
        root.addStretch()

        # 하단 버튼
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._launch_btn = QPushButton("시작")
        self._launch_btn.setFixedSize(120, 40)
        self._launch_btn.setStyleSheet(
            "QPushButton { background: #1976d2; color: white; font-size: 14px;"
            " border-radius: 4px; }"
            "QPushButton:hover { background: #1565c0; }"
            "QPushButton:disabled { background: #444; color: #777; }"
        )
        self._launch_btn.setEnabled(False)
        self._launch_btn.clicked.connect(self._on_launch)
        btn_row.addWidget(self._launch_btn)
        root.addLayout(btn_row)

        self._eq_cards: list[_EquipmentCard] = []

    # ── 프로젝트 로딩 ─────────────────────────────────────────────────────────

    def _load_projects(self) -> None:
        self._projects.clear()
        for card in self._eq_cards:
            card.deleteLater()
        self._eq_cards.clear()

        project_dirs = sorted(_PROJECTS_DIR.iterdir()) if _PROJECTS_DIR.exists() else []
        col = 0
        for proj_dir in project_dirs:
            yaml_path = proj_dir / "project.yaml"
            if not yaml_path.exists():
                continue
            try:
                with open(yaml_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except Exception:
                continue

            proj_info = data.get("project", {})
            project_name = proj_dir.name
            eq_type = proj_info.get("equipment_type", project_name)
            icon = _EQUIPMENT_ICONS.get(eq_type, "⚙️")

            card = _EquipmentCard(
                project_name=project_name,
                display_name=proj_info.get("name", project_name),
                description=proj_info.get("description", ""),
                icon=icon,
            )
            card.sig_selected.connect(self._on_card_selected)
            self._eq_cards.append(card)
            self._eq_grid.addWidget(card, 0, col)
            col += 1
            self._projects.append({"name": project_name, "info": proj_info})

        if self._eq_cards:
            self._eq_cards[0].set_selected(True)
            self._selected_project = self._eq_cards[0].project_name
            self._launch_btn.setEnabled(True)

    # ── 슬롯 ─────────────────────────────────────────────────────────────────

    def _on_card_selected(self, project_name: str) -> None:
        self._selected_project = project_name
        for card in self._eq_cards:
            card.set_selected(card.project_name == project_name)
        self._launch_btn.setEnabled(True)

    def _on_launch(self) -> None:
        if not self._selected_project:
            QMessageBox.warning(self, "선택 오류", "장비를 선택해주세요.")
            return
        mode_btn = self._mode_group.checkedButton()
        mode = mode_btn.property("mode") if mode_btn else "standalone"
        self.sig_launch.emit(self._selected_project, mode)


# ── 장비 선택 카드 ────────────────────────────────────────────────────────────

class _EquipmentCard(QWidget):
    """장비 한 개를 나타내는 클릭 가능한 카드."""

    sig_selected = pyqtSignal(str)  # project_name

    _STYLE_NORMAL = (
        "QWidget { border: 2px solid #444; border-radius: 8px;"
        " background: #2a2a2a; padding: 8px; }"
        "QWidget:hover { border-color: #666; background: #303030; }"
    )
    _STYLE_SELECTED = (
        "QWidget { border: 2px solid #1976d2; border-radius: 8px;"
        " background: #1a2a3a; padding: 8px; }"
    )

    def __init__(
        self,
        project_name: str,
        display_name: str,
        description: str,
        icon: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.project_name = project_name
        self.setFixedSize(190, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(icon, display_name, description)
        self.set_selected(False)

    def _build(self, icon: str, name: str, desc: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px; border: none; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        name_label = QLabel(name)
        name_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #e0e0e0;"
            " border: none; background: transparent;"
        )
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        desc_label = QLabel(desc[:40] + "…" if len(desc) > 40 else desc)
        desc_label.setStyleSheet(
            "font-size: 10px; color: #888; border: none; background: transparent;"
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

    def set_selected(self, selected: bool) -> None:
        self.setStyleSheet(self._STYLE_SELECTED if selected else self._STYLE_NORMAL)

    def mousePressEvent(self, event) -> None:
        self.sig_selected.emit(self.project_name)
