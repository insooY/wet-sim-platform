"""ConfigLoader / schema 단위 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.config.config_loader import ConfigLoader
from src.config.schema import ValidationError, validate_equipment, validate_recipe


# ── 픽스처 — 실제 프로젝트 설정 사용 ─────────────────────────────────────────

@pytest.fixture
def loader():
    return ConfigLoader()


# ── ConfigLoader ──────────────────────────────────────────────────────────────

def test_load_batch_spray_equipment(loader):
    cfg = loader.load_equipment("batch_spray")
    assert "equipment" in cfg
    assert cfg["equipment"]["type"] == "batch_spray"


def test_load_single_spin_equipment(loader):
    cfg = loader.load_equipment("single_spin")
    assert cfg["equipment"]["type"] == "single_spin"


def test_load_batch_immersion_equipment(loader):
    cfg = loader.load_equipment("batch_immersion")
    assert cfg["equipment"]["type"] == "batch_immersion"
    assert "baths" in cfg


def test_load_all_recipes_batch_spray(loader):
    recipes = loader.load_all_recipes("batch_spray")
    assert len(recipes) >= 1
    assert "recipe" in recipes[0]


def test_load_all_recipes_single_spin(loader):
    recipes = loader.load_all_recipes("single_spin")
    assert len(recipes) >= 1
    assert recipes[0]["recipe"]["name"] == "SC1 Spin Clean"


def test_load_all_recipes_batch_immersion(loader):
    recipes = loader.load_all_recipes("batch_immersion")
    assert len(recipes) >= 1
    assert recipes[0]["recipe"]["name"] == "SC1 Immersion Clean"


def test_load_project_returns_project_section(loader):
    proj = loader.load_project("batch_spray")
    assert "project" in proj


def test_load_chemistry_db(loader):
    db = loader.load_chemistry_db()
    assert "chemicals" in db
    assert "SC1" in db["chemicals"]
    assert "DIW" in db["chemicals"]


def test_load_nonexistent_file_raises(loader):
    with pytest.raises(FileNotFoundError):
        loader.load("projects/no_such_project/equipment.yaml")


# ── validate_equipment ────────────────────────────────────────────────────────

def _base_cfg(**overrides) -> dict:
    cfg = {
        "equipment": {
            "name": "Test Eq",
            "type": "batch_spray",
            "wafer_size": "300mm",
            "cassette_slots": 25,
            "loadports": 1,
        },
        "motors": [],
        "valves": [],
        "sensors": [],
        "heaters": [],
    }
    cfg["equipment"].update(overrides)
    return cfg


def test_validate_equipment_passes_for_real_configs(loader):
    for project in ("batch_spray", "single_spin", "batch_immersion"):
        cfg = loader.load_equipment(project)
        validate_equipment(cfg)   # 예외 없어야 함


def test_validate_equipment_missing_name_raises():
    cfg = _base_cfg()
    del cfg["equipment"]["name"]
    with pytest.raises(ValidationError, match="name"):
        validate_equipment(cfg)


def test_validate_equipment_invalid_type_raises():
    cfg = _base_cfg(type="unknown_type")
    with pytest.raises(ValidationError, match="type"):
        validate_equipment(cfg)


def test_validate_equipment_all_valid_types():
    for eq_type in ("batch_spray", "single_spin", "batch_immersion"):
        cfg = _base_cfg(type=eq_type)
        validate_equipment(cfg)   # 예외 없어야 함


def test_validate_motor_missing_id_raises():
    cfg = _base_cfg()
    cfg["motors"] = [{"name": "M", "type": "servo",
                       "range": [0, 100], "max_speed": 10, "accel": 5}]
    with pytest.raises(ValidationError, match="id"):
        validate_equipment(cfg)


def test_validate_motor_invalid_range_raises():
    cfg = _base_cfg()
    cfg["motors"] = [{"id": "M1", "name": "M", "type": "servo",
                       "range": 100, "max_speed": 10, "accel": 5}]
    with pytest.raises(ValidationError, match="range"):
        validate_equipment(cfg)


def test_validate_valve_missing_response_ms_raises():
    cfg = _base_cfg()
    cfg["valves"] = [{"id": "V1", "name": "V", "type": "pneumatic"}]
    with pytest.raises(ValidationError, match="response_ms"):
        validate_equipment(cfg)


def test_validate_sensor_missing_unit_raises():
    cfg = _base_cfg()
    cfg["sensors"] = [{"id": "S1", "name": "S", "type": "temperature",
                        "range": [0, 100]}]
    with pytest.raises(ValidationError, match="unit"):
        validate_equipment(cfg)


def test_validate_heater_missing_power_kw_raises():
    cfg = _base_cfg()
    cfg["heaters"] = [{"id": "H1", "name": "H", "target_range": [20, 80]}]
    with pytest.raises(ValidationError, match="power_kw"):
        validate_equipment(cfg)


# ── validate_recipe ───────────────────────────────────────────────────────────

def _base_recipe(**overrides) -> dict:
    """실제 YAML 구조: recipe(메타) + steps(최상위) 분리."""
    cfg = {
        "recipe": {"name": "Test Recipe", "description": "desc"},
        "steps": [
            {"name": "Step 1", "duration": 10},
            {"name": "Step 2", "duration": 5},
        ],
    }
    # overrides는 steps 교체용
    cfg.update(overrides)
    return cfg


def test_validate_recipe_passes_for_real_recipes(loader):
    for project in ("batch_spray", "single_spin", "batch_immersion"):
        for recipe in loader.load_all_recipes(project):
            validate_recipe(recipe)   # 예외 없어야 함


def test_validate_recipe_missing_recipe_key_raises():
    with pytest.raises(ValidationError, match="recipe"):
        validate_recipe({"steps": []})


def test_validate_recipe_missing_name_raises():
    cfg = _base_recipe()
    del cfg["recipe"]["name"]
    with pytest.raises(ValidationError, match="name"):
        validate_recipe(cfg)


def test_validate_recipe_missing_steps_raises():
    cfg = _base_recipe()
    del cfg["steps"]
    with pytest.raises(ValidationError, match="steps"):
        validate_recipe(cfg)


def test_validate_recipe_steps_not_list_raises():
    cfg = _base_recipe()
    cfg["steps"] = "not a list"
    with pytest.raises(ValidationError, match="리스트"):
        validate_recipe(cfg)


def test_validate_recipe_step_missing_name_raises():
    cfg = _base_recipe()
    cfg["steps"] = [{"duration": 10}]
    with pytest.raises(ValidationError, match="name"):
        validate_recipe(cfg)


def test_validate_recipe_empty_steps_is_valid():
    cfg = _base_recipe()
    cfg["steps"] = []
    validate_recipe(cfg)   # 빈 스텝은 유효


def test_validate_recipe_all_projects_pass(loader):
    for project in ("batch_spray", "single_spin", "batch_immersion"):
        for recipe_data in loader.load_all_recipes(project):
            validate_recipe(recipe_data)
