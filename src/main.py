import sys

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
