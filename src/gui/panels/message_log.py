"""메시지 로그 패널 — Connected Mode RX/TX 메시지 실시간 표시."""
from __future__ import annotations

import time
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

_MAX_LINES = 500


class MessageLogPanel(QWidget):
    """RX(수신)/TX(송신) 메시지를 색상으로 구분하여 표시하는 패널."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_count = 0
        self._source: list[dict] | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("메시지 로그")
        title.setStyleSheet("font-weight: bold; font-size: 11px; color: #ccc;")
        header.addWidget(title)
        header.addStretch()

        self._status_label = QLabel("● 미연결")
        self._status_label.setStyleSheet("color: #888; font-size: 11px;")
        header.addWidget(self._status_label)

        clear_btn = QPushButton("지우기")
        clear_btn.setFixedHeight(20)
        clear_btn.setFixedWidth(50)
        clear_btn.setStyleSheet("font-size: 10px;")
        clear_btn.clicked.connect(self._clear)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(_MAX_LINES)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self._log.setFont(font)
        self._log.setStyleSheet(
            "QPlainTextEdit { background: #1a1a1a; color: #ddd; border: 1px solid #333; }"
        )
        layout.addWidget(self._log)

    # ── public API ───────────────────────────────────────────────────────────

    def set_source(self, message_log: list[dict]) -> None:
        """ConnectedSession.message_log 리스트를 연결한다."""
        self._source = message_log
        self._last_count = 0

    def set_connected(self, connected: bool) -> None:
        if connected:
            self._status_label.setText("● 연결됨")
            self._status_label.setStyleSheet("color: #4caf50; font-size: 11px;")
        else:
            self._status_label.setText("● 미연결")
            self._status_label.setStyleSheet("color: #888; font-size: 11px;")

    def refresh(self) -> None:
        """새 메시지를 로그에 추가한다. Qt 타이머로 주기적 호출."""
        if self._source is None:
            return
        new_msgs = self._source[self._last_count:]
        self._last_count = len(self._source)
        for msg in new_msgs:
            self._append(msg)

    # ── 내부 ─────────────────────────────────────────────────────────────────

    def _append(self, msg: dict[str, Any]) -> None:
        direction = msg.get("dir", "??")
        topic     = msg.get("topic", "")
        payload   = msg.get("payload", {})
        ts_ms     = msg.get("ts", 0)
        t         = time.strftime("%H:%M:%S", time.localtime(ts_ms / 1000))

        # heartbeat는 표시 생략
        if "heartbeat" in topic:
            return

        payload_short = str(payload)
        if len(payload_short) > 80:
            payload_short = payload_short[:77] + "..."

        line = f"[{t}] {direction:2} {topic:<35} {payload_short}"

        cursor = self._log.textCursor()
        from PyQt6.QtGui import QTextCursor, QTextCharFormat
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        if direction == "TX":
            fmt.setForeground(QColor("#64b5f6"))   # 파란색
        elif direction == "RX":
            fmt.setForeground(QColor("#81c784"))   # 녹색
        else:
            fmt.setForeground(QColor("#aaa"))

        cursor.insertText(line + "\n", fmt)
        self._log.setTextCursor(cursor)
        self._log.ensureCursorVisible()

    def _clear(self) -> None:
        self._log.clear()
        if self._source is not None:
            self._source.clear()
        self._last_count = 0
