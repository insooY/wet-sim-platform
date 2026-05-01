from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from src.gui.widgets.common import CardWidget


class SequencePanel(QWidget):
    """레시피 스텝 진행 상황을 표시하는 패널."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = CardWidget("Recipe Progress")

        self._recipe_label = QLabel("—")
        self._recipe_label.setObjectName("RecipeName")
        card.content_layout().addWidget(self._recipe_label)

        self._step_label = QLabel("Step: —")
        self._step_label.setWordWrap(True)
        card.content_layout().addWidget(self._step_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("%v / %m steps")
        card.content_layout().addWidget(self._progress_bar)

        self._step_counter = QLabel("0 / 0")
        self._step_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        card.content_layout().addWidget(self._step_counter)

        layout.addWidget(card)
        layout.addStretch()

    def set_recipe_name(self, name: str) -> None:
        self._recipe_label.setText(name)

    def update_progress(self, current_step: int, total_steps: int, step_name: str) -> None:
        self._step_label.setText(f"Step: {step_name}")
        self._step_counter.setText(f"{current_step + 1} / {total_steps}")
        pct = int((current_step + 1) / total_steps * 100) if total_steps > 0 else 0
        self._progress_bar.setMaximum(total_steps)
        self._progress_bar.setValue(current_step + 1)
        self._progress_bar.setFormat(f"%v / {total_steps} steps")

    def reset(self) -> None:
        self._recipe_label.setText("—")
        self._step_label.setText("Step: —")
        self._progress_bar.setValue(0)
        self._step_counter.setText("0 / 0")
