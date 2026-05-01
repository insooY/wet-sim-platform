from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class CardWidget(QFrame):
    """제목 + 콘텐츠를 감싸는 테두리 카드."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("CardWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        layout.addWidget(title_label)

        self._content = QVBoxLayout()
        self._content.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._content)

    def content_layout(self) -> QVBoxLayout:
        return self._content


class StatusLabel(QLabel):
    """색상 점 + 텍스트 상태 표시 라벨."""

    _COLORS: dict[str, str] = {
        "idle":    "#9e9e9e",
        "ready":   "#66bb6a",
        "running": "#42a5f5",
        "paused":  "#ffa726",
        "error":   "#ef5350",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._status = "idle"
        self._update()

    def set_status(self, status: str, text: str | None = None) -> None:
        self._status = status.lower()
        display = text or status.upper()
        color = self._COLORS.get(self._status, "#9e9e9e")
        self.setText(f'<span style="color:{color};">●</span> {display}')

    def _update(self) -> None:
        self.set_status(self._status)


class ValueGauge(QWidget):
    """이름 + 현재값 + 단위 + 프로그레스 바 게이지."""

    def __init__(
        self,
        label: str,
        unit: str = "",
        min_val: float = 0.0,
        max_val: float = 100.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._unit = unit

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = QLabel(label)
        header.setObjectName("GaugeLabel")
        layout.addWidget(header)

        self._value_label = QLabel("—")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._value_label)

        self._bar = QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setMaximum(1000)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        layout.addWidget(self._bar)

    def update_value(self, value: float) -> None:
        import math
        if math.isnan(value):
            self._value_label.setText(f'<span style="color:#ef5350;">FAULT</span>')
            self._bar.setValue(0)
            return
        self._value_label.setText(f"{value:.2f} {self._unit}")
        ratio = (value - self._min) / (self._max - self._min) if self._max != self._min else 0
        self._bar.setValue(int(max(0.0, min(1.0, ratio)) * 1000))
