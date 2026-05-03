"""Settings > Baths 탭 — 배스 구성 편집 (주로 batch_immersion 용)."""
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

_CHEMICALS = ["SC1", "SC2", "DHF", "BHF", "SPM", "DIW", "IPA", "ozone", "H3PO4"]


def _item(text: str) -> QTableWidgetItem:
    return QTableWidgetItem(str(text))


class BathTab(QWidget):
    """Settings > Baths 탭."""

    HEADERS = ["ID", "이름", "케미컬", "온도 (°C)", "침지 시간 (s)", "메가소닉", "오버플로"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        note = QLabel("배스 구성은 Batch Immersion 장비에 적용됩니다.")
        note.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(note)

        self._table = QTableWidget(0, len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        for label, slot in [("+ 추가", self._add), ("- 삭제", self._remove),
                             ("▲ 위로", self._move_up), ("▼ 아래로", self._move_down)]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ── 버튼 핸들러 ──────────────────────────────────────────────────────────

    def _add(self) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        n = row + 1
        self._table.setItem(row, 0, _item(f"bath_{n}"))
        self._table.setItem(row, 1, _item(f"Bath {n}"))
        self._set_chem_combo(row, "DIW")
        self._table.setItem(row, 3, _item("23"))
        self._table.setItem(row, 4, _item("300"))
        self._set_bool_combo(row, 5, False)
        self._set_bool_combo(row, 6, False)

    def _remove(self) -> None:
        rows = sorted({i.row() for i in self._table.selectedIndexes()}, reverse=True)
        for r in rows:
            self._table.removeRow(r)

    def _move_up(self) -> None:
        row = self._table.currentRow()
        if row > 0:
            self._swap_rows(row, row - 1)
            self._table.setCurrentCell(row - 1, 0)

    def _move_down(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < self._table.rowCount() - 1:
            self._swap_rows(row, row + 1)
            self._table.setCurrentCell(row + 1, 0)

    def _swap_rows(self, a: int, b: int) -> None:
        for col in range(self._table.columnCount()):
            wa = self._table.cellWidget(a, col)
            wb = self._table.cellWidget(b, col)
            if wa and wb:
                # 콤보박스 값만 교환
                if isinstance(wa, QComboBox) and isinstance(wb, QComboBox):
                    va, vb = wa.currentText(), wb.currentText()
                    wa.setCurrentText(vb)
                    wb.setCurrentText(va)
            else:
                ia = self._table.takeItem(a, col)
                ib = self._table.takeItem(b, col)
                if ia:
                    self._table.setItem(b, col, ia)
                if ib:
                    self._table.setItem(a, col, ib)

    # ── 위젯 헬퍼 ────────────────────────────────────────────────────────────

    def _set_chem_combo(self, row: int, value: str) -> None:
        combo = QComboBox()
        combo.addItems(_CHEMICALS)
        idx = combo.findText(value)
        combo.setCurrentIndex(max(idx, 0))
        self._table.setCellWidget(row, 2, combo)

    def _set_bool_combo(self, row: int, col: int, value: bool) -> None:
        combo = QComboBox()
        combo.addItems(["false", "true"])
        combo.setCurrentIndex(1 if value else 0)
        self._table.setCellWidget(row, col, combo)

    def _cell(self, row: int, col: int) -> str:
        it = self._table.item(row, col)
        return it.text().strip() if it else ""

    def _combo_val(self, row: int, col: int) -> str:
        w = self._table.cellWidget(row, col)
        return w.currentText() if w else ""

    # ── public API ───────────────────────────────────────────────────────────

    def load_config(self, cfg: dict[str, Any]) -> None:
        self._table.setRowCount(0)
        for b in cfg.get("baths", []):
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, _item(b.get("id", "")))
            self._table.setItem(row, 1, _item(b.get("name", "")))
            self._set_chem_combo(row, b.get("chemistry", "DIW"))
            self._table.setItem(row, 3, _item(str(b.get("temperature", 23))))
            self._table.setItem(row, 4, _item(str(b.get("dip_time_sec", 300))))
            self._set_bool_combo(row, 5, bool(b.get("megasonic", False)))
            self._set_bool_combo(row, 6, bool(b.get("overflow", False)))

    def get_config(self) -> dict[str, Any]:
        baths = []
        for row in range(self._table.rowCount()):
            baths.append({
                "id":           self._cell(row, 0),
                "name":         self._cell(row, 1),
                "chemistry":    self._combo_val(row, 2),
                "temperature":  _to_float(self._cell(row, 3)),
                "dip_time_sec": _to_int(self._cell(row, 4)),
                "megasonic":    self._combo_val(row, 5) == "true",
                "overflow":     self._combo_val(row, 6) == "true",
            })
        return {"baths": baths}


def _to_float(s: str) -> float:
    try:
        return float(s)
    except ValueError:
        return 0.0


def _to_int(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        return 0
