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

        self._build_turntable_cassette()

    def _build_turntable_cassette(self) -> None:
        """턴테이블 디스크 + 그 위에 올라가는 카세트 박스."""
        # ── 턴테이블 ──────────────────────────────────────────────────────────
        # 챔버 바닥에서 20 mm 위, 반지름 220 mm, 높이 30 mm 원통 디스크
        turntable = vtkCylinderSource()
        turntable.SetRadius(220)
        turntable.SetHeight(30)
        turntable.SetResolution(48)

        self._actor_turntable = _make_actor(turntable, (0.55, 0.55, 0.6))
        # VTK 실린더 기본축이 Y축 → Z축으로 세우기 위해 X 방향 90° 회전
        self._actor_turntable.RotateX(90)
        self._actor_turntable.SetPosition(0, 0, 35)   # 바닥 + 두께/2
        self._scene.add_actor("turntable", self._actor_turntable)

        # ── 카세트 ────────────────────────────────────────────────────────────
        # 25-slot 카세트: 200(X) × 120(Y) × 300(Z) mm, 턴테이블 위
        cassette = vtkCubeSource()
        cassette.SetXLength(200)
        cassette.SetYLength(120)
        cassette.SetZLength(300)

        self._actor_cassette = _make_actor(cassette, (0.7, 0.7, 0.3))
        self._actor_cassette.SetPosition(0, 0, 50 + 150)  # 터너테이블 top + 카세트 중심
        self._scene.add_actor("cassette", self._actor_cassette)

        # 카세트 슬롯 선 — 얇은 박스 24개로 웨이퍼 구분선 표시
        slot_h = 300 / 25
        for i in range(24):
            slot_line = vtkCubeSource()
            slot_line.SetXLength(202)
            slot_line.SetYLength(2)
            slot_line.SetZLength(2)
            actor_slot = _make_actor(slot_line, (0.3, 0.3, 0.1))
            z = 50 + slot_h * (i + 1)
            actor_slot.SetPosition(0, 0, z)
            self._scene.add_actor(f"cassette_slot_{i}", actor_slot)

        self._build_nozzle_arm()

    def _build_nozzle_arm(self) -> None:
        """스윙 노즐 암 + 매니폴드 노즐 헤드."""
        # ── 로봇 암 기둥 (우측 벽에 부착) ────────────────────────────────────
        post = vtkCylinderSource()
        post.SetRadius(15)
        post.SetHeight(700)
        post.SetResolution(16)
        actor_post = _make_actor(post, (0.45, 0.45, 0.5))
        actor_post.RotateX(90)                         # Y → Z축
        actor_post.SetPosition(260, 0, 400)            # 챔버 우측 안쪽
        self._scene.add_actor("arm_post", actor_post)

        # ── 수평 암 (기둥에서 챔버 중심 방향으로 뻗음) ───────────────────────
        arm = vtkCubeSource()
        arm.SetXLength(300)
        arm.SetYLength(20)
        arm.SetZLength(20)
        self._actor_arm = _make_actor(arm, (0.5, 0.5, 0.55))
        self._actor_arm.SetPosition(110, 0, 500)       # 기둥 중심 → 챔버 중심쪽
        self._scene.add_actor("nozzle_arm", self._actor_arm)

        # ── 노즐 헤드 — 암 끝단에 달린 매니폴드 바 ──────────────────────────
        manifold = vtkCubeSource()
        manifold.SetXLength(20)
        manifold.SetYLength(180)
        manifold.SetZLength(20)
        actor_manifold = _make_actor(manifold, (0.4, 0.42, 0.45))
        actor_manifold.SetPosition(-40, 0, 500)
        self._scene.add_actor("nozzle_manifold", actor_manifold)

        # ── 노즐 팁 — 매니폴드에 등간격으로 붙은 원뿔형 노즐 5개 ─────────────
        from vtkmodules.vtkFiltersSources import vtkConeSource
        for i in range(5):
            nozzle = vtkConeSource()
            nozzle.SetHeight(30)
            nozzle.SetRadius(8)
            nozzle.SetResolution(12)
            actor_nozzle = _make_actor(nozzle, (0.2, 0.6, 0.8))
            y = -80 + i * 40
            actor_nozzle.RotateZ(90)                   # 팁이 아래(−Z)를 향하도록
            actor_nozzle.SetPosition(-40, y, 483)
            self._scene.add_actor(f"nozzle_tip_{i}", actor_nozzle)
