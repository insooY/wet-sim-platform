from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkRenderWindow
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from PyQt6.QtWidgets import QWidget, QVBoxLayout


class SceneManager(QWidget):
    """VTK 렌더러를 PyQt6 위젯에 임베딩하는 3D 씬 관리자."""

    BACKGROUND_TOP    = (0.12, 0.12, 0.18)
    BACKGROUND_BOTTOM = (0.05, 0.05, 0.08)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._actors: dict[str, object] = {}
        self._build_vtk()

    def _build_vtk(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self._vtk_widget)

        self._renderer = vtkRenderer()
        self._renderer.SetBackground2(*self.BACKGROUND_TOP)
        self._renderer.SetBackground(*self.BACKGROUND_BOTTOM)
        self._renderer.SetGradientBackground(True)

        render_window: vtkRenderWindow = self._vtk_widget.GetRenderWindow()
        render_window.AddRenderer(self._renderer)

        style = vtkInteractorStyleTrackballCamera()
        self._vtk_widget.GetRenderWindow().GetInteractor().SetInteractorStyle(style)

    def initialize(self) -> None:
        """MainWindow.show() 이후에 호출 — VTK 인터랙터를 초기화한다."""
        self._vtk_widget.Initialize()

    def add_actor(self, name: str, actor: object) -> None:
        self._renderer.AddActor(actor)
        self._actors[name] = actor

    def remove_actor(self, name: str) -> None:
        actor = self._actors.pop(name, None)
        if actor:
            self._renderer.RemoveActor(actor)

    def get_actor(self, name: str) -> object | None:
        return self._actors.get(name)

    def render(self) -> None:
        self._vtk_widget.GetRenderWindow().Render()

    def reset_camera(self) -> None:
        self._renderer.ResetCamera()
        self.render()

    @property
    def renderer(self) -> vtkRenderer:
        return self._renderer
