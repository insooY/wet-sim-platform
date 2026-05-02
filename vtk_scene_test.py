"""
SceneManager + BatchSprayModel 단독 렌더링 테스트.
python vtk_scene_test.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Python 3.8+: 확장 DLL 탐색 경로에 Python 실행 파일 디렉토리 추가
# MSYS2 ucrt64에서 vtkRenderingOpenGL2 의존 DLL을 찾기 위해 필요
_python_bin = Path(sys.executable).parent
if _python_bin.exists():
    os.add_dll_directory(str(_python_bin))

import vtkmodules.vtkRenderingOpenGL2  # noqa: F401, E402 — OpenGL 렌더러 팩토리 등록

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
        rw = self._scene.GetRenderWindow()
        print(f"RenderWindow class : {rw.GetClassName()}")
        print(f"RenderWindow size  : {rw.GetSize()}")
        print(f"Renderer count     : {rw.GetNumberOfLayers()}")

        print("_load_scene: building BatchSprayModel...")
        self._model = BatchSprayModel(self._scene)
        print(f"Actor count        : {self._scene.renderer.GetActors().GetNumberOfItems()}")

        self._scene.reset_camera()
        self._camera.set_isometric()
        self._scene.render()
        self._scene.update()   # Qt 위젯 강제 repaint
        print("render() done")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec())
