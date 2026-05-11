"""Single Wafer Spin Cleaner 3D 파라메트릭 모델.

좌표계: X=좌우, Y=전후, Z=상하 (단위: mm)
원점: 챔버 바닥 중심
"""
from vtkmodules.vtkFiltersSources import (
    vtkConeSource, vtkCubeSource, vtkCylinderSource, vtkDiskSource,
)
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from src.visualizer.scene_manager import SceneManager


def _actor(source, color: tuple, opacity: float = 1.0) -> vtkActor:
    m = vtkPolyDataMapper()
    m.SetInputConnection(source.GetOutputPort())
    a = vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(*color)
    a.GetProperty().SetOpacity(opacity)
    return a


class SingleSpinModel:
    """Single Wafer Spin Cleaner 장비 3D 파라메트릭 모델.

    구성: 원형 컵(드레인 볼) + 스핀 척 + 웨이퍼 + 스윙 노즐 암
    """

    CHAMBER_R = 280   # 컵 반지름 (mm)
    CHAMBER_H = 200   # 컵 높이

    def __init__(self, scene: SceneManager) -> None:
        self._scene = scene
        self._build()

    def _build(self) -> None:
        self._build_cup()
        self._build_chuck()
        self._build_wafer()
        self._build_nozzle_arm()

    def _build_cup(self) -> None:
        """원형 드레인 컵 — 외벽 실린더 + 반투명 내부."""
        r, h = self.CHAMBER_R, self.CHAMBER_H
        color_wall = (0.3, 0.35, 0.4)

        # 외벽
        outer = vtkCylinderSource()
        outer.SetRadius(r)
        outer.SetHeight(h)
        outer.SetResolution(48)
        outer.CappingOff()
        a_outer = _actor(outer, color_wall, opacity=0.6)
        a_outer.RotateX(90)
        a_outer.SetPosition(0, 0, h / 2)
        self._scene.add_actor("cup_outer", a_outer)

        # 바닥
        floor_src = vtkDiskSource()
        floor_src.SetInnerRadius(0)
        floor_src.SetOuterRadius(r)
        floor_src.SetRadialResolution(1)
        floor_src.SetCircumferentialResolution(48)
        a_floor = _actor(floor_src, (0.2, 0.22, 0.25))
        a_floor.RotateX(90)
        a_floor.SetPosition(0, 0, 0)
        self._scene.add_actor("cup_floor", a_floor)

        # 내부 반투명
        inner = vtkCylinderSource()
        inner.SetRadius(r - 8)
        inner.SetHeight(h - 2)
        inner.SetResolution(48)
        inner.CappingOff()
        a_inner = _actor(inner, (0.5, 0.75, 0.9), opacity=0.08)
        a_inner.RotateX(90)
        a_inner.SetPosition(0, 0, h / 2)
        self._scene.add_actor("cup_inner", a_inner)

    def _build_chuck(self) -> None:
        """스핀 척 — 컵 바닥 위에 놓이는 소형 원통 디스크."""
        chuck = vtkCylinderSource()
        chuck.SetRadius(155)   # 300 mm 웨이퍼 기준 반지름 155 mm
        chuck.SetHeight(20)
        chuck.SetResolution(48)

        self._actor_chuck = _actor(chuck, (0.5, 0.52, 0.58))
        self._actor_chuck.RotateX(90)
        self._actor_chuck.SetPosition(0, 0, 30)   # 바닥 + 높이/2
        self._scene.add_actor("spin_chuck", self._actor_chuck)

        # 진공 핀 3개
        for i in range(3):
            import math
            angle = math.radians(i * 120)
            pin = vtkCylinderSource()
            pin.SetRadius(6)
            pin.SetHeight(15)
            pin.SetResolution(8)
            ap = _actor(pin, (0.7, 0.7, 0.75))
            ap.RotateX(90)
            ap.SetPosition(120 * math.cos(angle), 120 * math.sin(angle), 47)
            self._scene.add_actor(f"chuck_pin_{i}", ap)

    def _build_wafer(self) -> None:
        """300 mm 실리콘 웨이퍼 — 얇은 디스크."""
        wafer = vtkDiskSource()
        wafer.SetInnerRadius(0)
        wafer.SetOuterRadius(150)
        wafer.SetRadialResolution(1)
        wafer.SetCircumferentialResolution(60)

        self._actor_wafer = _actor(wafer, (0.7, 0.7, 0.85), opacity=0.9)
        self._actor_wafer.RotateX(90)
        self._actor_wafer.SetPosition(0, 0, 41)   # 척 위에 올림
        self._actor_wafer.GetProperty().SetSpecular(0.8)
        self._actor_wafer.GetProperty().SetSpecularPower(50)
        self._scene.add_actor("wafer", self._actor_wafer)

    def _build_nozzle_arm(self) -> None:
        """스윙 노즐 암 — 한쪽에서 웨이퍼 중심으로 스윙."""
        # 기둥
        post = vtkCylinderSource()
        post.SetRadius(12)
        post.SetHeight(300)
        post.SetResolution(12)
        ap = _actor(post, (0.45, 0.45, 0.5))
        ap.RotateX(90)
        ap.SetPosition(240, 0, 180)
        self._scene.add_actor("arm_post", ap)

        # 수평 암
        arm = vtkCubeSource()
        arm.SetXLength(200)
        arm.SetYLength(15)
        arm.SetZLength(15)
        self._actor_arm = _actor(arm, (0.5, 0.5, 0.55))
        self._actor_arm.SetPosition(140, 0, 300)
        self._scene.add_actor("nozzle_arm", self._actor_arm)

        # 노즐 팁
        tip = vtkConeSource()
        tip.SetHeight(25)
        tip.SetRadius(7)
        tip.SetResolution(10)
        at = _actor(tip, (0.2, 0.6, 0.8))
        at.RotateZ(90)
        at.SetPosition(40, 0, 288)
        self._scene.add_actor("nozzle_tip", at)
