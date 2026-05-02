import random
import time

from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkFiltersGeneral import vtkVertexGlyphFilter
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper


from src.visualizer.scene_manager import SceneManager


class SprayParticleSystem:
    """노즐 팁에서 아래 방향으로 분사되는 스프레이 파티클 시스템.

    VTK vtkPolyData 포인트를 매 tick마다 갱신하여 파티클을 표현한다.
    """

    MAX_PARTICLES = 400
    EMIT_RATE = 20          # tick당 생성 파티클 수
    LIFETIME = 1.2          # 파티클 수명(초)
    SPEED_Z = -180.0        # 초기 Z속도 (아래 방향, mm/s)
    SPREAD_XY = 25.0        # XY 초기 확산 반경 (mm/s)
    GRAVITY = -600.0        # 중력 가속도 (mm/s²)

    def __init__(
        self,
        scene: SceneManager,
        emit_positions: list[tuple[float, float, float]],
        color: tuple[float, float, float] = (0.3, 0.7, 1.0),
        actor_name: str = "spray_particles",
    ) -> None:
        self._scene = scene
        self._emit_positions = emit_positions
        self._active = False
        self._last_tick = time.monotonic()

        # 파티클 상태: [x, y, z, vx, vy, vz, born_time]
        self._particles: list[list[float]] = []

        self._points = vtkPoints()
        self._polydata = vtkPolyData()
        self._polydata.SetPoints(self._points)

        glyph = vtkVertexGlyphFilter()
        glyph.SetInputData(self._polydata)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(glyph.GetOutputPort())

        self._actor = vtkActor()
        self._actor.SetMapper(mapper)
        self._actor.GetProperty().SetColor(*color)
        self._actor.GetProperty().SetPointSize(3)
        self._actor.GetProperty().SetOpacity(0.8)

        self._scene.add_actor(actor_name, self._actor)

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self) -> None:
        self._active = True
        self._last_tick = time.monotonic()

    def stop(self) -> None:
        self._active = False
        self._particles.clear()
        self._flush()

    def tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now

        # 수명 초과 파티클 제거
        self._particles = [
            p for p in self._particles if now - p[6] < self.LIFETIME
        ]

        # 신규 파티클 생성
        if self._active and len(self._particles) < self.MAX_PARTICLES:
            for _ in range(self.EMIT_RATE):
                origin = random.choice(self._emit_positions)
                vx = random.uniform(-self.SPREAD_XY, self.SPREAD_XY)
                vy = random.uniform(-self.SPREAD_XY, self.SPREAD_XY)
                self._particles.append([
                    origin[0], origin[1], origin[2],
                    vx, vy, self.SPEED_Z,
                    now,
                ])

        # 위치 갱신 (중력 포함)
        for p in self._particles:
            p[5] += self.GRAVITY * dt   # vz 누적
            p[0] += p[3] * dt
            p[1] += p[4] * dt
            p[2] += p[5] * dt

        self._flush()

    def _flush(self) -> None:
        """파티클 위치를 VTK 포인트에 반영한다."""
        self._points.Reset()
        for p in self._particles:
            self._points.InsertNextPoint(p[0], p[1], p[2])
        self._points.Modified()
        self._polydata.Modified()
