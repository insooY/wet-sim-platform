import sys
from pathlib import Path

# 직접 실행 시(python src/main.py) 프로젝트 루트를 sys.path에 추가
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PyQt6.QtWidgets import QApplication

from src.gui.selection_screen import SelectionScreen
from src.gui.main_window import MainWindow

_main_window: MainWindow | None = None   # GC 방지용 전역 참조


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Wet Process Simulator")

    # CLI에서 프로젝트를 바로 지정할 경우 선택 화면 생략
    if len(sys.argv) >= 2:
        project = sys.argv[1]
        mode = sys.argv[2] if len(sys.argv) >= 3 else "standalone"
        _launch(project, mode)
        sys.exit(app.exec())

    selector = SelectionScreen()

    def on_launch(proj: str, mode: str) -> None:
        selector.hide()
        _launch(proj, mode)

    selector.sig_launch.connect(on_launch)
    selector.show()

    sys.exit(app.exec())


def _launch(project: str, mode: str) -> None:
    global _main_window
    _main_window = MainWindow(project_name=project)
    _main_window._mode = mode   # 향후 Connected 모드 전달용
    _main_window.show()


if __name__ == "__main__":
    main()
