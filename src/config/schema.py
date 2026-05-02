"""equipment.yaml 구조 검증 스키마."""
from typing import Any


class ValidationError(Exception):
    """스키마 검증 실패."""


def _require(d: dict, key: str, ctx: str) -> Any:
    if key not in d:
        raise ValidationError(f"{ctx}: '{key}' 필드가 없습니다")
    return d[key]


def _validate_equipment_section(eq: dict) -> None:
    ctx = "equipment"
    for k in ("name", "type", "wafer_size", "cassette_slots", "loadports"):
        _require(eq, k, ctx)

    valid_types = {"batch_spray", "single_spin", "batch_immersion"}
    if eq["type"] not in valid_types:
        raise ValidationError(f"equipment.type: '{eq['type']}' 는 {valid_types} 중 하나여야 합니다")


def _validate_motor(m: dict, idx: int) -> None:
    ctx = f"motors[{idx}] (id={m.get('id', '?')})"
    for k in ("id", "name", "type", "range", "max_speed", "accel"):
        _require(m, k, ctx)
    r = m["range"]
    if not (isinstance(r, (list, tuple)) and len(r) == 2):
        raise ValidationError(f"{ctx}.range: [min, max] 형식이어야 합니다")


def _validate_valve(v: dict, idx: int) -> None:
    ctx = f"valves[{idx}] (id={v.get('id', '?')})"
    for k in ("id", "name", "type", "response_ms"):
        _require(v, k, ctx)


def _validate_sensor(s: dict, idx: int) -> None:
    ctx = f"sensors[{idx}] (id={s.get('id', '?')})"
    for k in ("id", "name", "type", "unit", "range"):
        _require(s, k, ctx)
    r = s["range"]
    if not (isinstance(r, (list, tuple)) and len(r) == 2):
        raise ValidationError(f"{ctx}.range: [min, max] 형식이어야 합니다")


def _validate_heater(h: dict, idx: int) -> None:
    ctx = f"heaters[{idx}] (id={h.get('id', '?')})"
    for k in ("id", "name", "power_kw", "target_range"):
        _require(h, k, ctx)


def validate_equipment(cfg: dict[str, Any]) -> None:
    """equipment.yaml 내용을 검증한다. 문제가 있으면 ValidationError를 발생시킨다."""
    _validate_equipment_section(_require(cfg, "equipment", "root"))

    for i, m in enumerate(cfg.get("motors", [])):
        _validate_motor(m, i)
    for i, v in enumerate(cfg.get("valves", [])):
        _validate_valve(v, i)
    for i, s in enumerate(cfg.get("sensors", [])):
        _validate_sensor(s, i)
    for i, h in enumerate(cfg.get("heaters", [])):
        _validate_heater(h, i)


def validate_recipe(cfg: dict[str, Any]) -> None:
    """recipe YAML 내용을 검증한다."""
    recipe = _require(cfg, "recipe", "root")
    _require(recipe, "name", "recipe")
    steps = _require(recipe, "steps", "recipe")
    if not isinstance(steps, list):
        raise ValidationError("recipe.steps: 리스트여야 합니다")
    for i, step in enumerate(steps):
        ctx = f"recipe.steps[{i}]"
        _require(step, "name", ctx)
        _require(step, "duration_sec", ctx)
