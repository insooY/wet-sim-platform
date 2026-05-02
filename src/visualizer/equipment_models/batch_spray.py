from vtkmodules.vtkFiltersSources import vtkCubeSource, vtkCylinderSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter

from src.visualizer.scene_manager import SceneManager


def _make_actor(source, color: tuple[float, float, float], opacity: float = 1.0) -> vtkActor:
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(source.GetOutputPort())
    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().SetOpacity(opacity)
    return actor


def _translated(source, dx: float, dy: float, dz: float) -> vtkTransformPolyDataFilter:
    t = vtkTransform()
    t.Translate(dx, dy, dz)
    tf = vtkTransformPolyDataFilter()
    tf.SetTransform(t)
    tf.SetInputConnection(source.GetOutputPort())
    return tf


class BatchSprayModel:
    """Batch Spray 장비 3D 파라메트릭 모델.

    좌표계: X=좌우, Y=전후, Z=상하 (단위: mm)
    원점: 챔버 바닥 중심
    """

    # 챔버 치수 (mm)
    CHAMBER_W = 600
    CHAMBER_D = 600
    CHAMBER_H = 800
    WALL = 10   # 벽 두께

    def __init__(self, scene: SceneManager) -> None:
        self._scene = scene
        self._build_chamber()

    def _build_chamber(self) -> None:
        """챔버 외벽 4면 + 바닥 (투명 전면으로 내부 보임)."""
        w, d, h, t = self.CHAMBER_W, self.CHAMBER_D, self.CHAMBER_H, self.WALL
        color = (0.3, 0.35, 0.4)

        # 후면 벽
        back = vtkCubeSource()
        back.SetXLength(w)
        back.SetYLength(t)
        back.SetZLength(h)
        actor_back = _make_actor(back, color)
        actor_back.SetPosition(0, d / 2, h / 2)
        self._scene.add_actor("chamber_back", actor_back)

        # 좌측 벽
        left = vtkCubeSource()
        left.SetXLength(t)
        left.SetYLength(d)
        left.SetZLength(h)
        actor_left = _make_actor(left, color)
        actor_left.SetPosition(-w / 2, 0, h / 2)
        self._scene.add_actor("chamber_left", actor_left)

        # 우측 벽
        right = vtkCubeSource()
        right.SetXLength(t)
        right.SetYLength(d)
        right.SetZLength(h)
        actor_right = _make_actor(right, color)
        actor_right.SetPosition(w / 2, 0, h / 2)
        self._scene.add_actor("chamber_right", actor_right)

        # 바닥
        floor = vtkCubeSource()
        floor.SetXLength(w)
        floor.SetYLength(d)
        floor.SetZLength(t)
        actor_floor = _make_actor(floor, (0.2, 0.22, 0.25))
        actor_floor.SetPosition(0, 0, -t / 2)
        self._scene.add_actor("chamber_floor", actor_floor)

        # 전면 — 반투명 유리
        front = vtkCubeSource()
        front.SetXLength(w)
        front.SetYLength(t)
        front.SetZLength(h)
        actor_front = _make_actor(front, (0.5, 0.75, 0.9), opacity=0.15)
        actor_front.GetProperty().SetAmbient(0.3)
        actor_front.SetPosition(0, -d / 2, h / 2)
        self._scene.add_actor("chamber_front", actor_front)
