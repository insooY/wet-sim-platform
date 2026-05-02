"""
SceneManager + BatchSprayModel 단독 렌더링 테스트.
python vtk_scene_test.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow

from src.visualizer.scene_manager import SceneManager
from src.visualizer.equipment_models.batch_spray import BatchSprayModel
from src.visualizer.camera_control import CameraControl


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Scene Test")
        self.resize(1200, 800)

        self._scene = SceneManager()
        self._camera = CameraControl(self._scene.renderer)
        self.setCentralWidget(self._scene)
        print("window ready")

    def showEvent(self, event):
        super().showEvent(event)
        print("showEvent: calling Initialize()")
        self._scene.Initialize()
        print("Initialize() done")
        QTimer.singleShot(50, self._load_scene)

    def _load_scene(self):
        print("_load_scene: building BatchSprayModel...")
        self._model = BatchSprayModel(self._scene)
        print("BatchSprayModel done")
        self._scene.reset_camera()
        self._camera.set_isometric()
        self._scene.render()
        print("render() done — 창에 장비가 보여야 합니다")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec())
