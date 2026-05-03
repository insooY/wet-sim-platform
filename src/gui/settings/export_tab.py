"""Settings > Export 탭 — 설정 요약 / YAML 미리보기."""
from typing import Any

import yaml

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSplitter,
    QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt


class ExportTab(QWidget):
    """Settings > Export 탭."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        note = QLabel("아래 YAML 미리보기는 OK 버튼을 누르면 equipment.yaml 파일로 저장됩니다.")
        note.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(note)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setFont(_monospace_font())
        self._preview.setPlaceholderText("설정 탭을 작성한 후 '미리보기 갱신' 버튼을 누르세요.")
        layout.addWidget(self._preview, stretch=1)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("미리보기 갱신")
        refresh_btn.clicked.connect(self._refresh_requested)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._refresh_cb: Any = None

    # ── public API ───────────────────────────────────────────────────────────

    def set_refresh_callback(self, cb: Any) -> None:
        """'미리보기 갱신' 클릭 시 호출할 콜백을 등록한다. cb()는 merged cfg dict를 반환해야 한다."""
        self._refresh_cb = cb

    def show_config(self, cfg: dict[str, Any]) -> None:
        """외부에서 직접 cfg를 전달하여 미리보기를 갱신한다."""
        text = yaml.dump(cfg, allow_unicode=True, sort_keys=False, default_flow_style=False)
        self._preview.setPlainText(text)

    def load_config(self, cfg: dict[str, Any]) -> None:
        self.show_config(cfg)

    def get_config(self) -> dict[str, Any]:
        return {}

    # ── 내부 ─────────────────────────────────────────────────────────────────

    def _refresh_requested(self) -> None:
        if self._refresh_cb:
            cfg = self._refresh_cb()
            if cfg:
                self.show_config(cfg)


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def _monospace_font():
    from PyQt6.QtGui import QFont
    f = QFont("Consolas", 9)
    f.setStyleHint(QFont.StyleHint.TypeWriter)
    return f
