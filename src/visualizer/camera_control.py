from vtkmodules.vtkRenderingCore import vtkRenderer


class CameraControl:
    """VTK 카메라 프리셋 및 리셋 유틸리티.

    마우스 궤도회전/팬/줌은 SceneManager가 설정한
    vtkInteractorStyleTrackballCamera가 자동으로 처리한다.
    이 클래스는 프리셋 뷰(등축/정면/상단)와 포커스 리셋을 제공한다.
    """

    def __init__(self, renderer: vtkRenderer) -> None:
        self._renderer = renderer

    def reset(self) -> None:
        """모든 액터가 보이도록 카메라를 자동 맞춤한다."""
        self._renderer.ResetCamera()
        self._render()

    def set_isometric(self) -> None:
        """등축(isometric) 뷰 — 장비 전체를 비스듬히 내려다본다."""
        camera = self._renderer.GetActiveCamera()
        bounds = self._get_bounds()
        cx, cy, cz = self._center(bounds)
        dist = self._diagonal(bounds) * 1.2

        camera.SetPosition(cx + dist, cy + dist * 0.6, cz + dist)
        camera.SetFocalPoint(cx, cy, cz)
        camera.SetViewUp(0, 0, 1)
        self._renderer.ResetCameraClippingRange()
        self._render()

    def set_front(self) -> None:
        """정면 뷰 (+Y 방향에서 바라본다)."""
        camera = self._renderer.GetActiveCamera()
        bounds = self._get_bounds()
        cx, cy, cz = self._center(bounds)
        dist = self._diagonal(bounds) * 1.2

        camera.SetPosition(cx, cy - dist, cz)
        camera.SetFocalPoint(cx, cy, cz)
        camera.SetViewUp(0, 0, 1)
        self._renderer.ResetCameraClippingRange()
        self._render()

    def set_top(self) -> None:
        """상단 뷰 (+Z 방향에서 아래로 내려다본다)."""
        camera = self._renderer.GetActiveCamera()
        bounds = self._get_bounds()
        cx, cy, cz = self._center(bounds)
        dist = self._diagonal(bounds) * 1.2

        camera.SetPosition(cx, cy, cz + dist)
        camera.SetFocalPoint(cx, cy, cz)
        camera.SetViewUp(0, 1, 0)
        self._renderer.ResetCameraClippingRange()
        self._render()

    # ── 내부 ─────────────────────────────────────────────────────────────────

    def _render(self) -> None:
        self._renderer.GetRenderWindow().Render()

    def _get_bounds(self) -> tuple[float, ...]:
        """씬 전체 bounding box를 반환한다. 액터가 없으면 기본값."""
        bounds = [0.0] * 6
        self._renderer.ComputeVisiblePropBounds(bounds)
        if all(b == 0.0 for b in bounds):
            return (-500.0, 500.0, -500.0, 500.0, -100.0, 900.0)
        return tuple(bounds)

    @staticmethod
    def _center(bounds: tuple) -> tuple[float, float, float]:
        return (
            (bounds[0] + bounds[1]) / 2,
            (bounds[2] + bounds[3]) / 2,
            (bounds[4] + bounds[5]) / 2,
        )

    @staticmethod
    def _diagonal(bounds: tuple) -> float:
        dx = bounds[1] - bounds[0]
        dy = bounds[3] - bounds[2]
        dz = bounds[5] - bounds[4]
        return (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5
