"""Settings UI에서 수정한 설정을 YAML 파일로 저장한다."""
from pathlib import Path
from typing import Any

import yaml


class ConfigWriter:
    """YAML 설정 파일 저장 유틸리티."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir else Path(__file__).parents[2] / "config"

    # ── public API ───────────────────────────────────────────────────────────

    def save_equipment(self, project_name: str, cfg: dict[str, Any]) -> Path:
        """equipment.yaml 을 저장하고 저장된 경로를 반환한다."""
        path = self._project_dir(project_name) / "equipment.yaml"
        self._write(path, cfg)
        return path

    def save_project(self, project_name: str, cfg: dict[str, Any]) -> Path:
        """project.yaml 을 저장하고 저장된 경로를 반환한다."""
        path = self._project_dir(project_name) / "project.yaml"
        self._write(path, cfg)
        return path

    def save_recipe(self, project_name: str, filename: str, cfg: dict[str, Any]) -> Path:
        """레시피 YAML 을 저장하고 저장된 경로를 반환한다."""
        recipes_dir = self._project_dir(project_name) / "recipes"
        recipes_dir.mkdir(parents=True, exist_ok=True)
        path = recipes_dir / filename
        self._write(path, cfg)
        return path

    def create_project(self, project_name: str) -> Path:
        """새 프로젝트 디렉토리를 생성하고 경로를 반환한다."""
        d = self._project_dir(project_name)
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── 내부 ────────────────────────────────────────────────────────────────

    def _project_dir(self, project_name: str) -> Path:
        return self._base / "projects" / project_name

    @staticmethod
    def _write(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
