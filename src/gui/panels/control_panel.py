from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.core.fsm import EquipmentState
from src.gui.widgets.common import CardWidget, StatusLabel


class ControlPanel(QWidget):
    """INIT / START / STOP / E-STOP 버튼 + 레시피 선택 + 상태 표시."""

    sig_init = pyqtSignal()
    sig_start = pyqtSignal(str)   # 선택된 레시피 이름
    sig_stop = pyqtSignal()
    sig_estop = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipe_names: list[str] = []
        self._build_ui()
        self.update_state(EquipmentState.IDLE)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # 상태 카드
        state_card = CardWidget("Equipment State")
        self._status_label = StatusLabel()
        state_card.content_layout().addWidget(self._status_label)
        root.addWidget(state_card)

        # 레시피 선택
        recipe_card = CardWidget("Recipe")
        self._recipe_combo = QComboBox()
        recipe_card.content_layout().addWidget(self._recipe_combo)
        root.addWidget(recipe_card)

        # 버튼
        btn_card = CardWidget("Control")
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)

        self._btn_init = QPushButton("INITIALIZE")
        self._btn_init.setObjectName("BtnInit")
        self._btn_init.clicked.connect(self.sig_init)

        self._btn_start = QPushButton("START")
        self._btn_start.setObjectName("BtnStart")
        self._btn_start.clicked.connect(self._on_start)

        self._btn_stop = QPushButton("STOP")
        self._btn_stop.setObjectName("BtnStop")
        self._btn_stop.clicked.connect(self.sig_stop)

        self._btn_estop = QPushButton("E-STOP")
        self._btn_estop.setObjectName("BtnEStop")
        self._btn_estop.clicked.connect(self.sig_estop)

        for btn in (self._btn_init, self._btn_start, self._btn_stop, self._btn_estop):
            btn.setMinimumHeight(36)
            btn_layout.addWidget(btn)

        btn_card.content_layout().addLayout(btn_layout)
        root.addWidget(btn_card)
        root.addStretch()

    def set_recipes(self, names: list[str]) -> None:
        self._recipe_names = names
        self._recipe_combo.clear()
        self._recipe_combo.addItems(names)

    def update_state(self, state: EquipmentState) -> None:
        s = state.name.lower()
        self._status_label.set_status(s, state.name)

        self._btn_init.setEnabled(state == EquipmentState.IDLE)
        self._btn_start.setEnabled(state == EquipmentState.READY)
        self._btn_stop.setEnabled(state in (EquipmentState.RUNNING, EquipmentState.PAUSED))
        self._btn_estop.setEnabled(state != EquipmentState.IDLE)

    def _on_start(self) -> None:
        name = self._recipe_combo.currentText()
        if name:
            self.sig_start.emit(name)
