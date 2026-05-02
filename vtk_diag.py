"""
VTK 단계별 진단 스크립트.
python vtk_diag.py
각 단계를 파일에도 기록하여 크래시 직전 단계를 확인한다.
"""
import sys
import os

LOG = open("vtk_diag_log.txt", "w", buffering=1)  # line-buffered


def p(msg: str) -> None:
    print(msg, flush=True)
    LOG.write(msg + "\n")
    LOG.flush()


p(f"Python: {sys.executable}")
p(f"Version: {sys.version}")
p(f"Platform: {sys.platform}")
p("")

p("STEP 1: PyQt6 import")
from PyQt6.QtWidgets import QApplication, QMainWindow
p("  OK")

p("STEP 2: vtkmodules.vtkFiltersSources import")
from vtkmodules.vtkFiltersSources import vtkCubeSource
p("  OK")

p("STEP 3: vtkmodules.vtkRenderingCore import")
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkActor, vtkPolyDataMapper
p("  OK")

p("STEP 4: vtkmodules.vtkInteractionStyle import")
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
p("  OK")

p("STEP 5: QVTKRenderWindowInteractor import")
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
p("  OK")

p("STEP 6: QApplication 생성")
app = QApplication(sys.argv)
p("  OK")

p("STEP 7: QVTKRenderWindowInteractor 인스턴스 생성")
vtk_widget = QVTKRenderWindowInteractor()
p("  OK")

p("STEP 8: GetRenderWindow 호출")
rw = vtk_widget.GetRenderWindow()
p("  OK")

p("STEP 9: vtkRenderer 생성 + AddRenderer")
ren = vtkRenderer()
ren.SetBackground(0.1, 0.1, 0.2)
rw.AddRenderer(ren)
p("  OK")

p("STEP 10: cube actor 추가")
cube = vtkCubeSource()
mapper = vtkPolyDataMapper()
mapper.SetInputConnection(cube.GetOutputPort())
actor = vtkActor()
actor.SetMapper(mapper)
actor.GetProperty().SetColor(1.0, 0.5, 0.2)
ren.AddActor(actor)
p("  OK")

p("STEP 11: QMainWindow에 centralWidget으로 설정 후 show()")
win = QMainWindow()
win.setCentralWidget(vtk_widget)
win.resize(800, 600)
win.show()
p("  OK")

p("STEP 12: vtk_widget.Initialize()")
vtk_widget.Initialize()
p("  OK")

p("STEP 13: rw.Render()")
ren.ResetCamera()
rw.Render()
p("  OK")

p("STEP 14: app.exec() — 창을 닫으면 종료")
ret = app.exec()
p(f"  종료 코드: {ret}")

LOG.close()
sys.exit(ret)
