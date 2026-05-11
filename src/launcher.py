"""System Launcher: 시뮬레이터 프로세스를 관리하고 자동으로 재시작한다.

실행:
    python -m src.launcher [project] [mode] [options]

옵션:
    --max-restarts N    최대 자동 재시작 횟수 (기본 5)
    --restart-delay S   재시작 전 대기 시간(초) (기본 3)
    --no-restart        재시작 비활성화

예시:
    python -m src.launcher batch_spray standalone
    python -m src.launcher single_spin connected --max-restarts 3
"""
from __future__ import annotations

import argparse
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

log = logging.getLogger("launcher")
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)

_ROOT = Path(__file__).resolve().parents[1]
_PYTHON = sys.executable

# 프로세스가 이 종료 코드로 끝나면 재시작하지 않음 (정상 종료)
_CLEAN_EXIT_CODES = {0}


class ProcessHandle:
    """단일 서브프로세스를 감싸는 핸들."""

    def __init__(self, args: list[str]) -> None:
        self._args = args
        self._proc: subprocess.Popen | None = None

    def start(self) -> None:
        log.info("프로세스 시작: %s", " ".join(self._args))
        self._proc = subprocess.Popen(
            self._args,
            cwd=str(_ROOT),
        )

    def stop(self, timeout: float = 5.0) -> None:
        if self._proc is None:
            return
        if self._proc.poll() is not None:
            return
        log.info("프로세스 종료 요청 (PID=%d)", self._proc.pid)
        self._proc.terminate()
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            log.warning("강제 종료 (PID=%d)", self._proc.pid)
            self._proc.kill()
            self._proc.wait()
        self._proc = None

    def wait(self) -> int:
        """프로세스가 끝날 때까지 대기하고 종료 코드를 반환."""
        if self._proc is None:
            return 0
        return self._proc.wait()

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc else None

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None


class Launcher:
    """프로세스 자동 재시작 관리자."""

    def __init__(
        self,
        project: str,
        mode: str,
        max_restarts: int = 5,
        restart_delay: float = 3.0,
        auto_restart: bool = True,
    ) -> None:
        self._project = project
        self._mode = mode
        self._max_restarts = max_restarts
        self._restart_delay = restart_delay
        self._auto_restart = auto_restart
        self._restart_count = 0
        self._handle: ProcessHandle | None = None
        self._running = False

        self._cmd = [_PYTHON, "-m", "src.main", project, mode]

    def run(self) -> None:
        """런처 메인 루프 — Ctrl+C 또는 max_restarts 초과 시 종료."""
        self._running = True
        self._register_signals()

        log.info("=== Wet Process Simulator Launcher ===")
        log.info("프로젝트: %s | 모드: %s", self._project, self._mode)
        log.info("자동 재시작: %s | 최대 %d회 | 대기 %.1f초",
                 self._auto_restart, self._max_restarts, self._restart_delay)

        while self._running:
            self._handle = ProcessHandle(self._cmd)
            self._handle.start()
            log.info("시뮬레이터 실행 중 (PID=%d, 재시작 %d/%d회)",
                     self._handle.pid, self._restart_count, self._max_restarts)

            exit_code = self._handle.wait()
            self._handle = None

            if not self._running:
                break

            if exit_code in _CLEAN_EXIT_CODES:
                log.info("정상 종료 (exit=%d) — 재시작 없음", exit_code)
                break

            log.warning("비정상 종료 (exit=%d)", exit_code)

            if not self._auto_restart:
                log.info("자동 재시작 비활성화 — 종료합니다.")
                break

            self._restart_count += 1
            if self._restart_count > self._max_restarts:
                log.error("최대 재시작 횟수(%d) 초과 — 종료합니다.", self._max_restarts)
                break

            log.info("%.1f초 후 재시작합니다... (%d/%d)",
                     self._restart_delay, self._restart_count, self._max_restarts)
            time.sleep(self._restart_delay)

        log.info("런처 종료.")

    def _register_signals(self) -> None:
        def _handler(signum, frame):
            log.info("신호 수신 (%s) — 종료합니다.", signal.Signals(signum).name)
            self._running = False
            if self._handle:
                self._handle.stop()

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wet Process Simulator 런처: 프로세스 자동 재시작 관리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "project",
        nargs="?",
        default="batch_spray",
        help="프로젝트 이름 (기본: batch_spray)",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="standalone",
        choices=["standalone", "connected"],
        help="운전 모드 (기본: standalone)",
    )
    parser.add_argument(
        "--max-restarts",
        type=int,
        default=5,
        metavar="N",
        help="최대 자동 재시작 횟수 (기본: 5)",
    )
    parser.add_argument(
        "--restart-delay",
        type=float,
        default=3.0,
        metavar="S",
        help="재시작 전 대기 시간(초) (기본: 3.0)",
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="자동 재시작 비활성화",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    launcher = Launcher(
        project=args.project,
        mode=args.mode,
        max_restarts=args.max_restarts,
        restart_delay=args.restart_delay,
        auto_restart=not args.no_restart,
    )
    launcher.run()
