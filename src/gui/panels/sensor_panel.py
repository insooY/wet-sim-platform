from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.gui.widgets.common import CardWidget, ValueGauge
from src.hal.hal_manager import HALManager


class SensorPanel(QWidget):
    """HALManager의 센서/히터 값을 실시간으로 표시하는 모니터링 패널."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gauges: dict[str, ValueGauge] = {}
        self._hal: HALManager | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._sensor_card = CardWidget("Sensors")
        layout.addWidget(self._sensor_card)

        self._heater_card = CardWidget("Heaters")
        layout.addWidget(self._heater_card)

        layout.addStretch()

    def load_hal(self, hal: HALManager) -> None:
        """HALManager를 주입받아 센서/히터 게이지를 동적으로 생성한다."""
        self._hal = hal
        self._gauges.clear()

        # 기존 위젯 제거
        for card in (self._sensor_card, self._heater_card):
            while card.content_layout().count():
                item = card.content_layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        for sid, sensor in hal.all_sensors().items():
            lo, hi = sensor.get_range()
            gauge = ValueGauge(
                label=sid,
                unit=sensor.get_unit(),
                min_val=lo,
                max_val=hi,
            )
            self._sensor_card.content_layout().addWidget(gauge)
            self._gauges[f"sensor_{sid}"] = gauge

        for hid, heater in hal.all_heaters().items():
            gauge = ValueGauge(
                label=hid,
                unit="°C",
                min_val=0.0,
                max_val=200.0,
            )
            self._heater_card.content_layout().addWidget(gauge)
            self._gauges[f"heater_{hid}"] = gauge

    def refresh(self) -> None:
        """타이머에서 주기적으로 호출 — 모든 센서/히터 값을 갱신한다."""
        if self._hal is None:
            return
        for sid, sensor in self._hal.all_sensors().items():
            gauge = self._gauges.get(f"sensor_{sid}")
            if gauge:
                gauge.update_value(sensor.read())
        for hid, heater in self._hal.all_heaters().items():
            gauge = self._gauges.get(f"heater_{hid}")
            if gauge:
                gauge.update_value(heater.get_current())
