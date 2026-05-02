import sys
from pathlib import Path

# 직접 실행 시(python src/main.py) 프로젝트 루트를 sys.path에 추가
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Wet Process Simulator")

    project = sys.argv[1] if len(sys.argv) > 1 else "batch_spray"
    window = MainWindow(project_name=project)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
