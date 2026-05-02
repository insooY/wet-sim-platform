"""
VTK+PyQt6 임베딩 진단 스크립트.
main.py 와 독립적으로 실행: python vtk_test.py
"""
import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkFiltersSources import vtkCubeSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VTK 임베딩 테스트")
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # VTK 위젯을 레이아웃 안에 배치 (실제 앱과 동일 구조)
        self._vtk = QVTKRenderWindowInteractor()
        self._vtk.setMinimumWidth(800)
        layout.addWidget(self._vtk, stretch=3)

        side = QWidget()
        side.setFixedWidth(300)
        layout.addWidget(side, stretch=1)

        # 렌더러 + 큐브 액터
        self._ren = vtkRenderer()
        self._ren.SetBackground(0.1, 0.1, 0.2)
        self._ren.SetBackground2(0.2, 0.2, 0.4)
        self._ren.SetGradientBackground(True)
        self._vtk.GetRenderWindow().AddRenderer(self._ren)

        style = vtkInteractorStyleTrackballCamera()
        self._vtk.GetRenderWindow().GetInteractor().SetInteractorStyle(style)

        cube = vtkCubeSource()
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(cube.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1.0, 0.5, 0.2)
        self._ren.AddActor(actor)

    def showEvent(self, event):
        super().showEvent(event)
        # 100 ms 뒤에 Initialize → 윈도우가 완전히 표시된 후 호출
        QTimer.singleShot(100, self._vtk_init)

    def _vtk_init(self):
        self._vtk.Initialize()
        self._ren.ResetCamera()
        self._vtk.GetRenderWindow().Render()
        print("[OK] VTK Render 완료 — 오렌지색 큐브가 보이면 VTK 정상")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec())
