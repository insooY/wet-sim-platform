"""테스트용 외부 GUI 클라이언트 — Connected Mode 시뮬레이터와 ZMQ로 통신한다.

실행:
    python -m src.connected.test_client
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor, QFont


class TestClient(QMainWindow):
    """시뮬레이터 연결 테스트용 최소 GUI."""

    PUB_PORT = 5556   # 클라이언트 → 시뮬레이터
    SUB_PORT = 5555   # 시뮬레이터 → 클라이언트

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simulator Test Client")
        self.resize(700, 600)
        self._ctx = None
        self._pub = None
        self._sub = None
        self._connected = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 연결 행
        conn_row = QHBoxLayout()
        self._host_edit = QLineEdit("127.0.0.1")
        self._host_edit.setFixedWidth(120)
        self._connect_btn = QPushButton("연결")
        self._connect_btn.setFixedWidth(70)
        self._connect_btn.clicked.connect(self._toggle_connect)
        self._status_lbl = QLabel("● 미연결")
        self._status_lbl.setStyleSheet("color: #888;")
        conn_row.addWidget(QLabel("Host:"))
        conn_row.addWidget(self._host_edit)
        conn_row.addWidget(self._connect_btn)
        conn_row.addWidget(self._status_lbl)
        conn_row.addStretch()
        layout.addLayout(conn_row)

        # 명령 패널
        cmd_box = QGroupBox("명령 전송")
        cmd_layout = QVBoxLayout(cmd_box)

        # 밸브
        v_row = QHBoxLayout()
        self._valve_combo = QComboBox()
        self._valve_combo.addItems(["V1", "V2", "V3", "V4"])
        v_open  = QPushButton("열기")
        v_close = QPushButton("닫기")
        v_open.clicked.connect(lambda: self._send_valve(self._valve_combo.currentText(), "open"))
        v_close.clicked.connect(lambda: self._send_valve(self._valve_combo.currentText(), "close"))
        v_row.addWidget(QLabel("밸브:"))
        v_row.addWidget(self._valve_combo)
        v_row.addWidget(v_open)
        v_row.addWidget(v_close)
        v_row.addStretch()
        cmd_layout.addLayout(v_row)

        # 모터
        m_row = QHBoxLayout()
        self._motor_combo = QComboBox()
        self._motor_combo.addItems(["M1", "M2"])
        self._pos_edit = QLineEdit("100.0")
        self._pos_edit.setFixedWidth(70)
        m_move = QPushButton("이동")
        m_move.clicked.connect(lambda: self._send_motor(
            self._motor_combo.currentText(),
            float(self._pos_edit.text() or "0")
        ))
        m_row.addWidget(QLabel("모터:"))
        m_row.addWidget(self._motor_combo)
        m_row.addWidget(QLabel("위치:"))
        m_row.addWidget(self._pos_edit)
        m_row.addWidget(m_move)
        m_row.addStretch()
        cmd_layout.addLayout(m_row)

        layout.addWidget(cmd_box)

        # 수신 로그
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(300)
        font = QFont("Consolas", 9)
        self._log.setFont(font)
        self._log.setStyleSheet(
            "QPlainTextEdit { background: #1a1a1a; color: #ddd; border: 1px solid #333; }"
        )
        layout.addWidget(self._log, stretch=1)

        # 수신 폴링 타이머
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start(100)

        # heartbeat 타이머
        self._hb_timer = QTimer(self)
        self._hb_timer.timeout.connect(self._send_heartbeat)
        self._hb_timer.start(1000)

    # ── 연결 ─────────────────────────────────────────────────────────────────

    def _toggle_connect(self) -> None:
        if not self._connected:
            self._do_connect()
        else:
            self._do_disconnect()

    def _do_connect(self) -> None:
        try:
            import zmq
            self._ctx = zmq.Context()
            self._pub = self._ctx.socket(zmq.PUB)
            self._pub.bind(f"tcp://127.0.0.1:{self.PUB_PORT}")
            self._sub = self._ctx.socket(zmq.SUB)
            self._sub.connect(f"tcp://127.0.0.1:{self.SUB_PORT}")
            self._sub.setsockopt(zmq.SUBSCRIBE, b"")
            self._sub.setsockopt(zmq.RCVTIMEO, 0)
            time.sleep(0.1)
            self._connected = True
            self._connect_btn.setText("연결 해제")
            self._status_lbl.setText("● 연결됨")
            self._status_lbl.setStyleSheet("color: #4caf50;")
            self._send_raw("system/connect", {"client": "TestClient"})
        except Exception as e:
            self._append_log(f"연결 실패: {e}", error=True)

    def _do_disconnect(self) -> None:
        if self._connected:
            self._send_raw("system/disconnect", {})
        self._connected = False
        self._connect_btn.setText("연결")
        self._status_lbl.setText("● 미연결")
        self._status_lbl.setStyleSheet("color: #888;")
        if self._pub:
            self._pub.close(linger=0)
        if self._sub:
            self._sub.close(linger=0)
        if self._ctx:
            self._ctx.term()
        self._pub = self._sub = self._ctx = None

    # ── 명령 전송 ─────────────────────────────────────────────────────────────

    def _send_valve(self, vid: str, action: str) -> None:
        self._send_raw(f"command/valve/{vid}", {"action": action})

    def _send_motor(self, mid: str, position: float) -> None:
        self._send_raw(f"command/motor/{mid}", {"action": "move", "position": position})

    def _send_heartbeat(self) -> None:
        if self._connected:
            self._send_raw("system/heartbeat", {"ts": int(time.time() * 1000)})

    def _send_raw(self, topic: str, payload: dict) -> None:
        if not self._pub:
            return
        msg = {"topic": topic, "timestamp": int(time.time() * 1000), "payload": payload}
        try:
            self._pub.send_string(json.dumps(msg))
            if "heartbeat" not in topic:
                self._append_log(f"TX {topic} {payload}", tx=True)
        except Exception:
            pass

    # ── 수신 폴링 ─────────────────────────────────────────────────────────────

    def _poll(self) -> None:
        if not self._sub:
            return
        try:
            while True:
                raw = self._sub.recv_string(flags=1)  # NOBLOCK
                msg = json.loads(raw)
                topic = msg.get("topic", "")
                payload = msg.get("payload", {})
                if "heartbeat" not in topic:
                    self._append_log(f"RX {topic} {str(payload)[:60]}")
        except Exception:
            pass

    # ── 로그 ─────────────────────────────────────────────────────────────────

    def _append_log(self, text: str, tx: bool = False, error: bool = False) -> None:
        cursor = self._log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        if error:
            fmt.setForeground(QColor("#ef5350"))
        elif tx:
            fmt.setForeground(QColor("#64b5f6"))
        else:
            fmt.setForeground(QColor("#81c784"))
        t = time.strftime("%H:%M:%S")
        cursor.insertText(f"[{t}] {text}\n", fmt)
        self._log.setTextCursor(cursor)
        self._log.ensureCursorVisible()

    def closeEvent(self, event) -> None:
        self._do_disconnect()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TestClient()
    w.show()
    sys.exit(app.exec())
