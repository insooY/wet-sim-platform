import sys
from pathlib import Path

# 직접 실행 시(python src/main.py) 프로젝트 루트를 sys.path에 추가
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PyQt6.QtWidgets import QApplication

from src.gui.selection_screen import SelectionScreen
from src.gui.main_window import MainWindow


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
    selector.sig_launch.connect(lambda proj, mode: _on_launch(selector, proj, mode))
    selector.show()

    sys.exit(app.exec())


def _on_launch(selector: SelectionScreen, project: str, mode: str) -> None:
    selector.hide()
    _launch(project, mode)


def _launch(project: str, mode: str) -> None:
    window = MainWindow(project_name=project)
    window.show()
    # mode는 향후 Connected 모드 구현 시 MainWindow에 전달
    window._mode = mode
