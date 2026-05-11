"""Batch Immersion Cleaner 3D 파라메트릭 모델.

좌표계: X=좌우(배스 나열 방향), Y=전후, Z=상하 (단위: mm)
원점: 첫 번째 배스 바닥 중심
"""
from vtkmodules.vtkFiltersSources import vtkCubeSource, vtkCylinderSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from src.visualizer.scene_manager import SceneManager

# 배스 치수 (mm)
_BATH_W   = 260   # 배스 폭 (X)
_BATH_D   = 300   # 배스 깊이 (Y)
_BATH_H   = 320   # 배스 높이 (Z)
_WALL     = 10    # 벽 두께
_BATH_GAP = 40    # 배스 간격 (X)

# 케미컬별 색상
_CHEM_COLORS = {
    "SC1":   (0.67, 0.28, 0.74),
    "SC2":   (0.26, 0.65, 0.96),
    "DHF":   (1.0,  0.65, 0.15),
    "BHF":   (1.0,  0.72, 0.30),
    "SPM":   (1.0,  0.42, 0.21),
    "DIW":   (0.31, 0.76, 1.0),
    "IPA":   (1.0,  0.98, 0.62),
    "ozone": (0.70, 1.0,  0.35),
    "H3PO4": (0.90, 0.45, 0.45),
}
_DEFAULT_LIQUID = (0.31, 0.76, 1.0)


def _actor(source, color: tuple, opacity: float = 1.0) -> vtkActor:
    m = vtkPolyDataMapper()
    m.SetInputConnection(source.GetOutputPort())
    a = vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(*color)
    a.GetProperty().SetOpacity(opacity)
    return a


class BatchImmersionModel:
    """Batch Immersion 장비 3D 파라메트릭 모델.

    baths 설정에 따라 배스 수와 케미컬 색상을 동적으로 구성한다.
    """

    def __init__(self, scene: SceneManager,
                 baths: list[dict] | None = None) -> None:
        self._scene = scene
        self._baths = baths or [
            {"id": "bath_1", "name": "SC-1",  "chemistry": "SC1"},
            {"id": "bath_2", "name": "QDR-1", "chemistry": "DIW"},
            {"id": "bath_3", "name": "DHF",   "chemistry": "DHF"},
            {"id": "bath_4", "name": "QDR-2", "chemistry": "DIW"},
        ]
        self._build()

    def _build(self) -> None:
        self._build_baths()
        self._build_lifter()
        self._build_robot()

    # ── 배스 ─────────────────────────────────────────────────────────────────

    def _build_baths(self) -> None:
        n = len(self._baths)
        # 전체 폭 중앙 기준 X 오프셋
        total_w = n * _BATH_W + (n - 1) * _BATH_GAP
        x_start = -total_w / 2 + _BATH_W / 2

        for i, bath in enumerate(self._baths):
            x = x_start + i * (_BATH_W + _BATH_GAP)
            chem = bath.get("chemistry", "DIW")
            self._build_one_bath(i, x, chem, bath.get("name", f"Bath{i+1}"))

    def _build_one_bath(self, idx: int, x: float, chem: str, name: str) -> None:
        w, d, h, t = _BATH_W, _BATH_D, _BATH_H, _WALL
        wall_color = (0.3, 0.35, 0.40)

        def add(suffix, source, color, pos, opacity=1.0):
            a = _actor(source, color, opacity)
            a.SetPosition(*pos)
            self._scene.add_actor(f"bath_{idx}_{suffix}", a)
            return a

        # 바닥
        fl = vtkCubeSource()
        fl.SetXLength(w); fl.SetYLength(d); fl.SetZLength(t)
        add("floor", fl, (0.2, 0.22, 0.25), (x, 0, -t / 2))

        # 후면
        bk = vtkCubeSource()
        bk.SetXLength(w); bk.SetYLength(t); bk.SetZLength(h)
        add("back", bk, wall_color, (x, d / 2, h / 2))

        # 좌측
        lw = vtkCubeSource()
        lw.SetXLength(t); lw.SetYLength(d); lw.SetZLength(h)
        add("left", lw, wall_color, (x - w / 2, 0, h / 2))

        # 우측
        rw = vtkCubeSource()
        rw.SetXLength(t); rw.SetYLength(d); rw.SetZLength(h)
        add("right", rw, wall_color, (x + w / 2, 0, h / 2))

        # 전면 반투명
        fr = vtkCubeSource()
        fr.SetXLength(w); fr.SetYLength(t); fr.SetZLength(h)
        a_front = _actor(fr, (0.5, 0.75, 0.9), opacity=0.12)
        a_front.SetPosition(x, -d / 2, h / 2)
        self._scene.add_actor(f"bath_{idx}_front", a_front)

        # 액체 채움 (80%)
        liquid_h = h * 0.80
        lq = vtkCubeSource()
        lq.SetXLength(w - t * 2)
        lq.SetYLength(d - t * 2)
        lq.SetZLength(liquid_h)
        liq_color = _CHEM_COLORS.get(chem, _DEFAULT_LIQUID)
        add("liquid", lq, liq_color, (x, 0, liquid_h / 2), opacity=0.35)

    # ── 리프터 ────────────────────────────────────────────────────────────────

    def _build_lifter(self) -> None:
        """배스 위를 가로지르는 리프터 빔 + 카세트."""
        n = len(self._baths)
        total_w = n * _BATH_W + (n - 1) * _BATH_GAP
        beam_z = _BATH_H + 120   # 배스 상단 + 여유

        # 수평 빔
        beam = vtkCubeSource()
        beam.SetXLength(total_w + 100)
        beam.SetYLength(30)
        beam.SetZLength(30)
        self._actor_lifter_beam = _actor(beam, (0.55, 0.55, 0.6))
        self._actor_lifter_beam.SetPosition(0, 0, beam_z)
        self._scene.add_actor("lifter_beam", self._actor_lifter_beam)

        # 수직 가이드 레일 (좌/우)
        for side in (-1, 1):
            rail = vtkCubeSource()
            rail.SetXLength(20)
            rail.SetYLength(20)
            rail.SetZLength(_BATH_H + 250)
            a = _actor(rail, (0.45, 0.45, 0.5))
            x_pos = side * (total_w / 2 + 60)
            a.SetPosition(x_pos, 0, (_BATH_H + 250) / 2)
            self._scene.add_actor(f"lifter_rail_{'l' if side < 0 else 'r'}", a)

        # 카세트 (리프터 빔에 매달림)
        cassette = vtkCubeSource()
        cassette.SetXLength(220)
        cassette.SetYLength(120)
        cassette.SetZLength(280)
        self._actor_cassette = _actor(cassette, (0.7, 0.7, 0.3))
        self._actor_cassette.SetPosition(0, 0, beam_z - 160)
        self._scene.add_actor("cassette", self._actor_cassette)

        # 카세트 슬롯 선 25개
        slot_h = 280 / 25
        cassette_bot = beam_z - 160 - 140
        for i in range(24):
            sl = vtkCubeSource()
            sl.SetXLength(222); sl.SetYLength(2); sl.SetZLength(2)
            a = _actor(sl, (0.3, 0.3, 0.1))
            a.SetPosition(0, 0, cassette_bot + slot_h * (i + 1))
            self._scene.add_actor(f"cassette_slot_{i}", a)

    # ── 이송 로봇 레일 ────────────────────────────────────────────────────────

    def _build_robot(self) -> None:
        """배스 앞쪽에 놓인 수평 이송 로봇 레일."""
        n = len(self._baths)
        total_w = n * _BATH_W + (n - 1) * _BATH_GAP

        rail = vtkCubeSource()
        rail.SetXLength(total_w + 200)
        rail.SetYLength(40)
        rail.SetZLength(40)
        a = _actor(rail, (0.4, 0.4, 0.45))
        a.SetPosition(0, -_BATH_D / 2 - 60, 60)
        self._scene.add_actor("robot_rail", a)

        # 로봇 캐리지
        carriage = vtkCubeSource()
        carriage.SetXLength(80); carriage.SetYLength(60); carriage.SetZLength(60)
        self._actor_robot = _actor(carriage, (0.6, 0.3, 0.3))
        self._actor_robot.SetPosition(-total_w / 2, -_BATH_D / 2 - 60, 60)
        self._scene.add_actor("robot_carriage", self._actor_robot)
