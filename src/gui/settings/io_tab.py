"""Settings > I/O Devices 탭 — 모터/밸브/센서/히터 편집."""
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)


# ── 공통 테이블 헬퍼 ──────────────────────────────────────────────────────────

def _item(text: str, editable: bool = True) -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    if not editable:
        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return it


class _TablePanel(QWidget):
    """디바이스 목록을 QTableWidget으로 편집하는 공통 패널."""

    HEADERS: list[str] = []       # 서브클래스에서 정의
    DEFAULT_ROW: list[str] = []   # 새 행 기본값

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._table = QTableWidget(0, len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ 추가")
        add_btn.clicked.connect(self._add_row)
        del_btn = QPushButton("- 삭제")
        del_btn.clicked.connect(self._del_row)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _add_row(self) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        for col, val in enumerate(self.DEFAULT_ROW):
            self._table.setItem(row, col, _item(val))
        self._fill_combos(row)

    def _del_row(self) -> None:
        rows = sorted(
            {idx.row() for idx in self._table.selectedIndexes()}, reverse=True
        )
        for row in rows:
            self._table.removeRow(row)

    def _fill_combos(self, row: int) -> None:
        """서브클래스에서 콤보박스 열을 오버라이드한다."""

    def _cell(self, row: int, col: int) -> str:
        it = self._table.item(row, col)
        return it.text().strip() if it else ""

    def _load_rows(self, rows: list[list[str]]) -> None:
        self._table.setRowCount(0)
        for vals in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            for col, val in enumerate(vals):
                self._table.setItem(r, col, _item(str(val)))
            self._fill_combos(r)

    def _all_rows(self) -> list[list[str]]:
        result = []
        for row in range(self._table.rowCount()):
            result.append([self._cell(row, col) for col in range(len(self.HEADERS))])
        return result


# ── 모터 ─────────────────────────────────────────────────────────────────────

class _MotorPanel(_TablePanel):
    HEADERS = ["ID", "이름", "타입", "범위 최소", "범위 최대", "최대 속도", "가속도"]
    DEFAULT_ROW = ["M?", "New Motor", "servo", "0", "360", "30.0", "10.0"]
    _TYPES = ["servo", "stepper"]

    def _fill_combos(self, row: int) -> None:
        combo = QComboBox()
        combo.addItems(self._TYPES)
        cur = self._cell(row, 2)
        idx = combo.findText(cur)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        self._table.setCellWidget(row, 2, combo)

    def load(self, motors: list[dict[str, Any]]) -> None:
        rows = []
        for m in motors:
            r = m.get("range", [0, 360])
            rows.append([
                m.get("id", ""), m.get("name", ""), m.get("type", "servo"),
                str(r[0]), str(r[1]),
                str(m.get("max_speed", 30.0)), str(m.get("accel", 10.0)),
            ])
        self._load_rows(rows)

    def get(self) -> list[dict[str, Any]]:
        result = []
        for row in range(self._table.rowCount()):
            combo = self._table.cellWidget(row, 2)
            type_val = combo.currentText() if combo else self._cell(row, 2)
            result.append({
                "id": self._cell(row, 0),
                "name": self._cell(row, 1),
                "type": type_val,
                "range": [_float(self._cell(row, 3)), _float(self._cell(row, 4))],
                "max_speed": _float(self._cell(row, 5)),
                "accel": _float(self._cell(row, 6)),
                "simulation": {},
            })
        return result


# ── 밸브 ─────────────────────────────────────────────────────────────────────

class _ValvePanel(_TablePanel):
    HEADERS = ["ID", "이름", "타입", "응답 시간 (ms)"]
    DEFAULT_ROW = ["V?", "New Valve", "pneumatic", "200"]
    _TYPES = ["pneumatic", "solenoid"]

    def _fill_combos(self, row: int) -> None:
        combo = QComboBox()
        combo.addItems(self._TYPES)
        cur = self._cell(row, 2)
        idx = combo.findText(cur)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        self._table.setCellWidget(row, 2, combo)

    def load(self, valves: list[dict[str, Any]]) -> None:
        rows = [
            [v.get("id", ""), v.get("name", ""),
             v.get("type", "pneumatic"), str(v.get("response_ms", 200))]
            for v in valves
        ]
        self._load_rows(rows)

    def get(self) -> list[dict[str, Any]]:
        result = []
        for row in range(self._table.rowCount()):
            combo = self._table.cellWidget(row, 2)
            type_val = combo.currentText() if combo else self._cell(row, 2)
            result.append({
                "id": self._cell(row, 0),
                "name": self._cell(row, 1),
                "type": type_val,
                "response_ms": _int(self._cell(row, 3)),
            })
        return result


# ── 센서 ─────────────────────────────────────────────────────────────────────

class _SensorPanel(_TablePanel):
    HEADERS = ["ID", "이름", "타입", "단위", "범위 최소", "범위 최대", "초기값", "노이즈", "Tau"]
    DEFAULT_ROW = ["S?", "New Sensor", "temperature", "°C", "0", "100", "25.0", "0.2", "5.0"]
    _TYPES = ["temperature", "flow", "pressure", "level", "humidity", "pH"]

    def _fill_combos(self, row: int) -> None:
        combo = QComboBox()
        combo.addItems(self._TYPES)
        cur = self._cell(row, 2)
        idx = combo.findText(cur)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        self._table.setCellWidget(row, 2, combo)

    def load(self, sensors: list[dict[str, Any]]) -> None:
        rows = []
        for s in sensors:
            r = s.get("range", [0, 100])
            sim = s.get("simulation", {})
            rows.append([
                s.get("id", ""), s.get("name", ""), s.get("type", "temperature"),
                s.get("unit", ""), str(r[0]), str(r[1]),
                str(s.get("initial_value", 0.0)),
                str(sim.get("noise", 0.1)), str(sim.get("response_tau", 5.0)),
            ])
        self._load_rows(rows)

    def get(self) -> list[dict[str, Any]]:
        result = []
        for row in range(self._table.rowCount()):
            combo = self._table.cellWidget(row, 2)
            type_val = combo.currentText() if combo else self._cell(row, 2)
            result.append({
                "id": self._cell(row, 0),
                "name": self._cell(row, 1),
                "type": type_val,
                "unit": self._cell(row, 3),
                "range": [_float(self._cell(row, 4)), _float(self._cell(row, 5))],
                "initial_value": _float(self._cell(row, 6)),
                "simulation": {
                    "noise": _float(self._cell(row, 7)),
                    "response_tau": _float(self._cell(row, 8)),
                },
            })
        return result


# ── 히터 ─────────────────────────────────────────────────────────────────────

class _HeaterPanel(_TablePanel):
    HEADERS = ["ID", "이름", "출력 (kW)", "목표 최소 (°C)", "목표 최대 (°C)", "Tau (s)"]
    DEFAULT_ROW = ["H?", "New Heater", "5.0", "20", "80", "25.0"]

    def load(self, heaters: list[dict[str, Any]]) -> None:
        rows = []
        for h in heaters:
            tr = h.get("target_range", [20, 80])
            rows.append([
                h.get("id", ""), h.get("name", ""),
                str(h.get("power_kw", 5.0)),
                str(tr[0]), str(tr[1]),
                str(h.get("tau", 25.0)),
            ])
        self._load_rows(rows)

    def get(self) -> list[dict[str, Any]]:
        result = []
        for row in range(self._table.rowCount()):
            result.append({
                "id": self._cell(row, 0),
                "name": self._cell(row, 1),
                "power_kw": _float(self._cell(row, 2)),
                "target_range": [_float(self._cell(row, 3)), _float(self._cell(row, 4))],
                "tau": _float(self._cell(row, 5)),
            })
        return result


# ── IOTab (메인) ──────────────────────────────────────────────────────────────

class IOTab(QWidget):
    """Settings > I/O Devices 탭."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        note = QLabel("셀을 클릭하여 직접 편집하세요. 콤보박스 열은 드롭다운으로 선택합니다.")
        note.setStyleSheet("color: #aaa; font-size: 11px; margin: 4px;")
        layout.addWidget(note)

        self._tabs = QTabWidget()
        self._motors = _MotorPanel()
        self._valves = _ValvePanel()
        self._sensors = _SensorPanel()
        self._heaters = _HeaterPanel()

        self._tabs.addTab(self._motors, "모터")
        self._tabs.addTab(self._valves, "밸브")
        self._tabs.addTab(self._sensors, "센서")
        self._tabs.addTab(self._heaters, "히터")
        layout.addWidget(self._tabs)

    # ── public API ───────────────────────────────────────────────────────────

    def load_config(self, cfg: dict[str, Any]) -> None:
        self._motors.load(cfg.get("motors", []))
        self._valves.load(cfg.get("valves", []))
        self._sensors.load(cfg.get("sensors", []))
        self._heaters.load(cfg.get("heaters", []))

    def get_config(self) -> dict[str, Any]:
        return {
            "motors":  self._motors.get(),
            "valves":  self._valves.get(),
            "sensors": self._sensors.get(),
            "heaters": self._heaters.get(),
        }


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def _float(s: str) -> float:
    try:
        return float(s)
    except ValueError:
        return 0.0


def _int(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        return 0
