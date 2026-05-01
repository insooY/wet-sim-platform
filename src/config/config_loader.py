from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    """YAML 파일을 로딩하고 필수 키를 검증한다."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir else Path(__file__).parents[2] / "config"

    def load(self, rel_path: str) -> dict[str, Any]:
        path = self._base / rel_path
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def load_system(self) -> dict[str, Any]:
        return self.load("system_config.yaml")

    def load_chemistry_db(self) -> dict[str, Any]:
        return self.load("chemistry_db.yaml")

    def load_project(self, project_name: str) -> dict[str, Any]:
        return self.load(f"projects/{project_name}/project.yaml")

    def load_equipment(self, project_name: str) -> dict[str, Any]:
        project = self.load_project(project_name)
        equipment_file = project.get("equipment_config", "equipment.yaml")
        return self.load(f"projects/{project_name}/{equipment_file}")

    def load_recipe(self, project_name: str, recipe_file: str) -> dict[str, Any]:
        return self.load(f"projects/{project_name}/{recipe_file}")

    def load_all_recipes(self, project_name: str) -> list[dict[str, Any]]:
        project = self.load_project(project_name)
        recipes = []
        for rel in project.get("recipes", []):
            data = self.load(f"projects/{project_name}/{rel}")
            recipes.append(data)
        return recipes
