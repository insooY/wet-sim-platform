"""ZeroMQ 메시지 토픽 상수 정의."""

# ── 센서 / 액추에이터 ────────────────────────────────────────────────────────
SENSOR_VALUE      = "sensor/{id}/value"        # 주기적
MOTOR_POSITION    = "motor/{id}/position"      # 주기적
MOTOR_STATUS      = "motor/{id}/status"        # 이벤트
VALVE_STATE       = "valve/{id}/state"         # 이벤트
HEATER_TEMP       = "heater/{id}/temperature"  # 주기적

# ── 장비 상태 ─────────────────────────────────────────────────────────────────
EQUIPMENT_STATE   = "equipment/state"          # 이벤트
EQUIPMENT_MODE    = "equipment/mode"           # 이벤트

# ── 알람 ─────────────────────────────────────────────────────────────────────
ALARM_NEW         = "alarm/new"
ALARM_CLEAR       = "alarm/clear"
INTERLOCK_TRIGGER = "interlock/trigger"

# ── 레시피 ────────────────────────────────────────────────────────────────────
RECIPE_START      = "recipe/start"
RECIPE_STEP       = "recipe/step"
RECIPE_COMPLETE   = "recipe/complete"

# ── 로트 ─────────────────────────────────────────────────────────────────────
LOT_START         = "lot/start"
LOT_COMPLETE      = "lot/complete"

# ── 시스템 ────────────────────────────────────────────────────────────────────
SYSTEM_HEARTBEAT  = "system/heartbeat"
SYSTEM_CONNECT    = "system/connect"
SYSTEM_CONNECTED  = "system/connected"
SYSTEM_DISCONNECT = "system/disconnect"


def sensor_value(sensor_id: str) -> str:
    return SENSOR_VALUE.format(id=sensor_id)

def motor_position(motor_id: str) -> str:
    return MOTOR_POSITION.format(id=motor_id)

def motor_status(motor_id: str) -> str:
    return MOTOR_STATUS.format(id=motor_id)

def valve_state(valve_id: str) -> str:
    return VALVE_STATE.format(id=valve_id)

def heater_temp(heater_id: str) -> str:
    return HEATER_TEMP.format(id=heater_id)
