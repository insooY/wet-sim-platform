import time
from typing import Callable

from vtkmodules.vtkRenderingCore import vtkActor


class AnimationBase:
    """단일 애니메이션 — tick()을 주기적으로 호출해 액터를 갱신한다."""

    def __init__(self) -> None:
        self._active = False
        self._start_time = 0.0

    def start(self) -> None:
        self._active = True
        self._start_time = time.monotonic()

    def stop(self) -> None:
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def tick(self, dt: float) -> None:
        """dt: 이전 tick 이후 경과 시간(초). 서브클래스에서 구현."""
        raise NotImplementedError


class RotateAnimation(AnimationBase):
    """액터를 지정 축 중심으로 연속 회전시킨다."""

    def __init__(
        self,
        actor: vtkActor,
        axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
        speed_deg_per_sec: float = 30.0,
    ) -> None:
        super().__init__()
        self._actor = actor
        self._axis = axis
        self._speed = speed_deg_per_sec

    def tick(self, dt: float) -> None:
        if not self._active:
            return
        deg = self._speed * dt
        self._actor.RotateWXYZ(deg, *self._axis)


class OscillateAnimation(AnimationBase):
    """액터를 지정 축 중심으로 ±amplitude 범위에서 왕복 운동시킨다."""

    def __init__(
        self,
        actor: vtkActor,
        axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
        amplitude_deg: float = 60.0,
        period_sec: float = 4.0,
    ) -> None:
        super().__init__()
        self._actor = actor
        self._axis = axis
        self._amplitude = amplitude_deg
        self._period = period_sec
        self._last_angle = 0.0

    def tick(self, dt: float) -> None:
        if not self._active:
            return
        import math
        elapsed = time.monotonic() - self._start_time
        angle = self._amplitude * math.sin(2 * math.pi * elapsed / self._period)
        delta = angle - self._last_angle
        self._last_angle = angle
        self._actor.RotateWXYZ(delta, *self._axis)


class ColorAnimation(AnimationBase):
    """액터 색상을 두 색 사이에서 보간한다."""

    def __init__(
        self,
        actor: vtkActor,
        color_from: tuple[float, float, float],
        color_to: tuple[float, float, float],
        duration_sec: float = 0.3,
        on_complete: Callable | None = None,
    ) -> None:
        super().__init__()
        self._actor = actor
        self._from = color_from
        self._to = color_to
        self._duration = duration_sec
        self._on_complete = on_complete
        self._elapsed = 0.0

    def tick(self, dt: float) -> None:
        if not self._active:
            return
        self._elapsed += dt
        t = min(self._elapsed / self._duration, 1.0)
        r = self._from[0] + (self._to[0] - self._from[0]) * t
        g = self._from[1] + (self._to[1] - self._from[1]) * t
        b = self._from[2] + (self._to[2] - self._from[2]) * t
        self._actor.GetProperty().SetColor(r, g, b)
        if t >= 1.0:
            self._active = False
            if self._on_complete:
                self._on_complete()


class AnimationManager:
    """등록된 모든 애니메이션을 tick()으로 일괄 갱신하고 렌더를 트리거한다."""

    def __init__(self, render_fn: Callable) -> None:
        self._render = render_fn
        self._animations: list[AnimationBase] = []
        self._last_tick = time.monotonic()

    def add(self, anim: AnimationBase) -> AnimationBase:
        self._animations.append(anim)
        return anim

    def remove(self, anim: AnimationBase) -> None:
        self._animations = [a for a in self._animations if a is not anim]

    def tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now

        active = [a for a in self._animations if a.is_active]
        if not active:
            return
        for anim in active:
            anim.tick(dt)
        self._render()
