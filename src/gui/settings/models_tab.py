"""Settings > 3D Models 탭 — 파트별 파라메트릭/CAD 소스 설정."""
from typing import Any

from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

_PARTS = ["chamber", "loadport", "turntable", "cassette", "nozzle", "arm", "lifter", "bath"]
_SOURCES = ["parametric", "cad"]


def _item(text: str) -> QTableWidgetItem:
    return QTableWidgetItem(str(text))


class ModelsTab(QWidget):
    """Settings > 3D Models 탭."""

    HEADERS = ["파트", "소스", "파일 (CAD 전용)", "스케일"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        note = QLabel("CAD 소스를 선택한 경우 glTF(.glb) 또는 STL(.stl) 파일을 지정하세요.")
        note.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(note)

        self._table = QTableWidget(0, len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        browse_btn = QPushButton("파일 선택...")
        browse_btn.clicked.connect(self._browse_cad)
        reset_btn = QPushButton("기본값으로 초기화")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(browse_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._reset_defaults()

    # ── 버튼 핸들러 ──────────────────────────────────────────────────────────

    def _browse_cad(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "CAD 파일 선택", "", "3D 파일 (*.glb *.gltf *.stl)"
        )
        if path:
            self._table.setItem(row, 2, _item(path))
            # 소스 콤보를 자동으로 cad로 변경
            combo = self._table.cellWidget(row, 1)
            if isinstance(combo, QComboBox):
                combo.setCurrentText("cad")

    def _reset_defaults(self) -> None:
        self._table.setRowCount(0)
        for part in _PARTS:
            self._add_part_row(part, "parametric", "", "1.0")

    def _add_part_row(self, part: str, source: str, file_path: str, scale: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, _item(part))

        combo = QComboBox()
        combo.addItems(_SOURCES)
        idx = combo.findText(source)
        combo.setCurrentIndex(max(idx, 0))
        self._table.setCellWidget(row, 1, combo)

        self._table.setItem(row, 2, _item(file_path))
        self._table.setItem(row, 3, _item(scale))

    # ── public API ───────────────────────────────────────────────────────────

    def load_config(self, cfg: dict[str, Any]) -> None:
        self._table.setRowCount(0)
        models = cfg.get("models", {})
        if not models:
            self._reset_defaults()
            return

        for part in _PARTS:
            m = models.get(part, {})
            source = m.get("source", "parametric")
            file_path = m.get("file", "")
            scale = str(m.get("scale", 1.0))
            self._add_part_row(part, source, file_path, scale)

    def get_config(self) -> dict[str, Any]:
        models: dict[str, Any] = {}
        for row in range(self._table.rowCount()):
            part = _cell(self._table, row, 0)
            combo = self._table.cellWidget(row, 1)
            source = combo.currentText() if isinstance(combo, QComboBox) else "parametric"
            file_path = _cell(self._table, row, 2)
            scale = _to_float(_cell(self._table, row, 3))

            entry: dict[str, Any] = {"source": source}
            if source == "cad" and file_path:
                entry["file"] = file_path
                entry["scale"] = scale
            models[part] = entry

        return {"models": models}


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def _cell(table: QTableWidget, row: int, col: int) -> str:
    it = table.item(row, col)
    return it.text().strip() if it else ""


def _to_float(s: str) -> float:
    try:
        return float(s)
    except ValueError:
        return 1.0
