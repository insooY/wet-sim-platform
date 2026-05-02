from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from PyQt6.QtWidgets import QWidget


class SceneManager(QVTKRenderWindowInteractor):
    """VTK 렌더러를 PyQt6에 임베딩 — QVTKRenderWindowInteractor를 직접 상속."""

    BACKGROUND_TOP    = (0.12, 0.12, 0.18)
    BACKGROUND_BOTTOM = (0.05, 0.05, 0.08)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._actors: dict[str, object] = {}
        self._setup_renderer()

    def _setup_renderer(self) -> None:
        self._renderer = vtkRenderer()
        self._renderer.SetBackground2(*self.BACKGROUND_TOP)
        self._renderer.SetBackground(*self.BACKGROUND_BOTTOM)
        self._renderer.SetGradientBackground(True)
        self.GetRenderWindow().AddRenderer(self._renderer)

        style = vtkInteractorStyleTrackballCamera()
        self.GetRenderWindow().GetInteractor().SetInteractorStyle(style)

    def initialize(self) -> None:
        """첫 렌더 트리거 — showEvent에서 Initialize() 호출 후 사용."""
        self.GetRenderWindow().Render()

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
        self.GetRenderWindow().Render()

    def reset_camera(self) -> None:
        self._renderer.ResetCamera()
        self.render()

    @property
    def renderer(self) -> vtkRenderer:
        return self._renderer
