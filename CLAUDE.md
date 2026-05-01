# Semiconductor Wet Process 3D Equipment Simulation Platform

## Project Overview

반도체 습식 세정장비 제어 소프트웨어 개발을 위한 **3D 시뮬레이션 플랫폼**.
실제 하드웨어 없이 GUI 프로그램, 드라이버, 공정 시퀀스를 검증하는 **개발 도구**다.

### 핵심 목적
1. **GUI 프로그램 테스트** — 외부 제어 GUI와 ZeroMQ로 연결하여 명령 수신/실행
2. **드라이버 테스트** — 모터, PLC, 센서 드라이버에 가짜 응답을 제공
3. **컨셉 시뮬레이션** — 배스 구성, 케미컬, 공정 시퀀스를 설정만으로 변경하여 검증
4. **3D 커스텀** — 설계 도면(CAD)을 파트별로 적용하여 실제 장비 형상으로 시뮬레이션

### 장비 타입 3종
- **Batch Spray**: 턴테이블 + 카세트(25 wafers) + 스프레이 노즐 매니폴드
- **Single Wafer Spin**: 스핀 척(3000rpm) + 매엽 + 스윙 노즐 암
- **Batch Immersion**: 다중 배스(가변) + 리프터 + 카세트 이송 로봇

### 운전 모드 2종
- **Standalone**: 자체 시뮬레이션 엔진으로 공정 자동 실행 + Fault Injection
- **Connected**: ZeroMQ로 외부 GUI 제어 프로그램과 연결하여 명령 수신/실행

## Tech Stack

- **Language**: Python 3.11+
- **GUI**: PyQt6
- **3D Engine**: VTK / PyVista (PyQt6 임베딩)
- **IPC**: ZeroMQ (pyzmq) — Pub/Sub 패턴
- **Config**: YAML (PyYAML)
- **DB**: SQLite (개발) / PostgreSQL + TimescaleDB (운영)
- **Build/Deploy**: PyInstaller (단일 exe)
- **Test**: pytest

## Architecture — 6 Layer

```
L6  Plugin System      서브 프로그램 (DB, Log, Alarm, SECS/GEM)
L5  3D Visualizer      3D 장비 렌더링 + 애니메이션 + Settings UI
L4  Equipment Core     FSM 상태 머신 + 레시피 실행 엔진
L3  HAL                하드웨어 추상화 (IMotor, IValve, ISensor, IHeater)
L2  Protocol           PLC 프로토콜 (S7, MC, ADS, Modbus, Simulator)
L1  Transport          물리 전송 (Serial, TCP, EtherCAT, Simulator)
```

각 레이어는 ABC(Abstract Base Class) 인터페이스로만 소통한다.
상위 레이어는 하위 레이어의 구체적 구현을 모른다.

### 핵심 설계 원칙
1. **인터페이스로 분리** — 바뀔 수 있는 것은 ABC 뒤에 숨긴다
2. **설정으로 조합** — YAML 변경만으로 하드웨어 구성, PLC, 통신 방식을 바꾼다
3. **메시지로 소통** — 프로세스 간 ZeroMQ Pub/Sub 메시지 사용
4. **시뮬레이터는 HAL의 가상 구현체** — 별도 프로그램이 아니라 HAL만 교체

## Directory Structure

```
wet-sim-platform/
├── CLAUDE.md
├── pyproject.toml
├── requirements.txt
├── README.md
│
├── config/
│   ├── system_config.yaml
│   ├── chemistry_db.yaml
│   └── projects/
│       ├── batch_spray/
│       │   ├── project.yaml
│       │   ├── equipment.yaml
│       │   ├── alarm.yaml
│       │   └── recipes/
│       │       ├── sc1_clean.yaml
│       │       └── dhf_clean.yaml
│       ├── single_spin/
│       │   ├── project.yaml
│       │   ├── equipment.yaml
│       │   └── recipes/
│       └── batch_immersion/
│           ├── project.yaml
│           ├── equipment.yaml
│           └── recipes/
│
├── src/
│   ├── __init__.py
│   ├── main.py                    # 엔트리 포인트
│   ├── launcher.py                # System Launcher (프로세스 관리)
│   │
│   ├── transport/                 # L1: 물리 전송
│   │   ├── __init__.py
│   │   ├── interfaces.py          # ITransport (ABC)
│   │   ├── serial_transport.py    # RS-232/485 (pyserial)
│   │   ├── tcp_transport.py       # Ethernet TCP (socket)
│   │   ├── ethercat_transport.py  # EtherCAT (pysoem)
│   │   └── simulator_transport.py # 루프백 (시뮬레이터용)
│   │
│   ├── protocol/                  # L2: PLC 프로토콜
│   │   ├── __init__.py
│   │   ├── interfaces.py          # IProtocol (ABC)
│   │   ├── siemens_s7.py          # Siemens S7 (python-snap7)
│   │   ├── mitsubishi_mc.py       # Mitsubishi MC (pymcprotocol)
│   │   ├── beckhoff_ads.py        # Beckhoff ADS (pyads)
│   │   ├── modbus.py              # Modbus RTU/TCP (pymodbus)
│   │   └── simulator_protocol.py  # Key-Value 메모리 (시뮬레이터용)
│   │
│   ├── hal/                       # L3: 하드웨어 추상화
│   │   ├── __init__.py
│   │   ├── interfaces.py          # IMotor, IValve, ISensor, IHeater (ABC)
│   │   ├── hal_manager.py         # HAL Manager (YAML → 인스턴스 생성, ID 조회)
│   │   ├── real_hal.py            # 실장비 HAL (Protocol을 통해 실제 I/O)
│   │   └── simulator_hal.py       # 시뮬레이터 HAL (물리 모델)
│   │
│   ├── core/                      # L4: 장비 제어 로직
│   │   ├── __init__.py
│   │   ├── fsm.py                 # FSM 상태 머신
│   │   ├── recipe_engine.py       # 레시피 YAML 파싱 + 순차 실행
│   │   └── equipment_manager.py   # 장비 전체 관리 (HAL + FSM + Recipe)
│   │
│   ├── visualizer/                # L5: 3D 시각화
│   │   ├── __init__.py
│   │   ├── scene_manager.py       # 3D 씬 관리 (VTK/PyVista)
│   │   ├── model_loader.py        # 모델 로더 (parametric / CAD import)
│   │   ├── equipment_models/      # 장비별 3D 모델 빌더
│   │   │   ├── __init__.py
│   │   │   ├── batch_spray.py
│   │   │   ├── single_spin.py
│   │   │   └── batch_immersion.py
│   │   ├── animation.py           # 애니메이션 시스템
│   │   ├── particles.py           # 파티클 시스템 (스프레이, 버블 등)
│   │   └── camera_control.py      # 카메라 궤도회전/팬/줌
│   │
│   ├── plugins/                   # L6: 서브 프로그램
│   │   ├── __init__.py
│   │   ├── plugin_interface.py    # IPlugin (ABC)
│   │   ├── plugin_loader.py       # 동적 플러그인 로딩
│   │   ├── db_manager/
│   │   │   ├── __init__.py
│   │   │   └── db_plugin.py
│   │   ├── log_manager/
│   │   │   ├── __init__.py
│   │   │   └── log_plugin.py
│   │   ├── alarm_manager/
│   │   │   ├── __init__.py
│   │   │   └── alarm_plugin.py
│   │   └── secs_gem/
│   │       ├── __init__.py
│   │       └── secs_plugin.py
│   │
│   ├── broker/                    # IPC 메시지 브로커
│   │   ├── __init__.py
│   │   ├── message_broker.py      # ZeroMQ Pub/Sub 래퍼
│   │   └── topics.py              # 토픽 상수 정의
│   │
│   ├── gui/                       # GUI 컴포넌트
│   │   ├── __init__.py
│   │   ├── main_window.py         # 메인 윈도우 (3D뷰 + 패널)
│   │   ├── selection_screen.py    # 장비/모드 선택 런처
│   │   ├── settings/              # Settings UI
│   │   │   ├── __init__.py
│   │   │   ├── settings_window.py # Settings 메인 윈도우
│   │   │   ├── equipment_tab.py   # 장비 타입/기본 설정
│   │   │   ├── bath_tab.py        # 배스 구성
│   │   │   ├── io_tab.py          # I/O 디바이스 (밸브/센서/모터/히터)
│   │   │   ├── comm_tab.py        # 통신 설정 (PLC/Transport)
│   │   │   ├── models_tab.py      # 3D 모델 (parametric/CAD)
│   │   │   └── export_tab.py      # 설정 저장/내보내기
│   │   ├── panels/
│   │   │   ├── control_panel.py   # START/STOP/CONNECT
│   │   │   ├── sensor_panel.py    # 센서값 모니터링
│   │   │   ├── valve_panel.py     # 밸브 상태
│   │   │   ├── sequence_panel.py  # 공정 시퀀스 진행
│   │   │   ├── fault_panel.py     # Fault Injection (Standalone)
│   │   │   └── message_log.py     # 메시지 로그 (Connected)
│   │   └── widgets/
│   │       ├── __init__.py
│   │       └── common.py          # 공용 위젯 (버튼, 카드, 게이지 등)
│   │
│   └── config/                    # 설정 관리
│       ├── __init__.py
│       ├── config_loader.py       # YAML 로딩 + 스키마 검증
│       ├── config_writer.py       # Settings UI → YAML 저장
│       └── schema.py              # 설정 스키마 정의
│
├── tests/
│   ├── __init__.py
│   ├── test_transport.py
│   ├── test_protocol.py
│   ├── test_hal.py
│   ├── test_fsm.py
│   ├── test_recipe.py
│   ├── test_broker.py
│   ├── test_plugins.py
│   └── test_config.py
│
└── assets/
    ├── models/                    # CAD import된 3D 모델 (.glb/.stl)
    ├── icons/
    └── styles/
        └── dark_theme.qss        # PyQt6 다크 테마 스타일시트
```

## Coding Conventions

### Interface Pattern (모든 레이어 동일)
```python
from abc import ABC, abstractmethod

class IMotor(ABC):
    """모터 하드웨어 추상화 인터페이스"""
    
    @abstractmethod
    def move_absolute(self, position: float) -> None: ...
    
    @abstractmethod
    def get_position(self) -> float: ...
    
    @abstractmethod
    def is_move_done(self) -> bool: ...
```

### Naming
- 인터페이스: `I` 접두사 (IMotor, IValve, ISensor, ITransport, IProtocol, IPlugin)
- 시뮬레이터 구현: `Sim` 접두사 (SimMotor, SimValve, SimSensor)
- 실장비 구현: `Real` 접두사 (RealMotor) 또는 제조사명 (SiemensS7Protocol)
- 파일명: snake_case
- 클래스명: PascalCase
- 메서드/변수: snake_case

### Type Hints
모든 함수/메서드에 type hint 필수:
```python
def read_sensor(self, sensor_id: str) -> float: ...
def load_config(self, path: str) -> dict[str, Any]: ...
```

### Message Format
ZeroMQ 메시지는 JSON 직렬화:
```python
{
    "topic": "sensor/S1/value",
    "timestamp": 1745875200000,
    "payload": {"value": 65.3, "unit": "°C", "quality": "good"}
}
```

### Topic Hierarchy
```
sensor/{id}/value          센서값 (주기적)
motor/{id}/position        모터 위치 (주기적)
motor/{id}/status          모터 상태 (이벤트)
valve/{id}/state           밸브 상태 (이벤트)
heater/{id}/temperature    히터 온도 (주기적)
equipment/state            장비 상태 전이 (이벤트)
equipment/mode             운전 모드 변경 (이벤트)
alarm/new                  알람 발생
alarm/clear                알람 해제
interlock/trigger          인터락 발동
recipe/start               레시피 시작
recipe/step                레시피 스텝 전환
recipe/complete            레시피 완료
lot/start                  로트 시작
lot/complete               로트 완료
system/heartbeat           프로세스 생존 확인
```

## Layer Specifications

### L1: Transport
- `ITransport.open(config: dict) -> bool`
- `ITransport.close() -> None`
- `ITransport.send(data: bytes) -> int`
- `ITransport.receive(max_len: int, timeout_ms: int) -> bytes`
- `ITransport.is_connected() -> bool`
- SimulatorTransport: 보낸 명령을 분석하여 가상 응답을 rxQueue에 넣고, receive에서 꺼내 돌려줌

### L2: Protocol
- `IProtocol.set_transport(transport: ITransport) -> None`
- `IProtocol.connect(config: dict) -> bool`
- `IProtocol.read_bool(address: str) -> bool`
- `IProtocol.write_bool(address: str, value: bool) -> None`
- `IProtocol.read_float(address: str) -> float`
- `IProtocol.write_float(address: str, value: float) -> None`
- SimulatorProtocol: dict[str, Any]를 내부 메모리로 사용, 주소 문자열을 키로 읽기/쓰기

### L3: HAL
```python
class IMotor(ABC):
    move_absolute(position: float) -> None
    move_relative(distance: float) -> None
    set_speed(speed: float) -> None
    get_position() -> float
    is_move_done() -> bool
    is_homed() -> bool
    stop() -> None
    home() -> None
    emergency_stop() -> None

class IValve(ABC):
    open() -> None
    close() -> None
    is_open() -> bool
    is_closed() -> bool
    get_response_ms() -> int

class ISensor(ABC):
    read() -> float
    get_unit() -> str
    get_range() -> tuple[float, float]
    is_healthy() -> bool

class IHeater(ABC):
    set_target(temperature: float) -> None
    get_target() -> float
    get_current() -> float
    enable() -> None
    disable() -> None
    is_at_target(tolerance: float = 0.5) -> bool
```

SimulatorHAL 물리 모델:
- **SimSensor**: 1차 지연 응답 (시정수 tau) + 가우시안 노이즈
  - `current += (target - current) * (dt / tau) + gaussian(0, noise_std)`
- **SimMotor**: 사다리꼴 가감속 (ACCEL → CRUISE → DECEL → DONE)
- **SimValve**: 응답 지연 (response_ms 경과 후 상태 변경)
- **SimHeater**: PID 응답 모델 (overshoot, settling time)

### L4: Equipment Core
- FSM 상태: IDLE → INITIALIZING → READY → RUNNING → PAUSED → ABORTING → IDLE
- 공정 스텝: LOADING → (배스/스프레이 시퀀스) → UNLOADING
- 레시피 YAML에서 스텝별 밸브/모터/온도/시간 로딩
- HAL 인터페이스만 호출 (구체적 하드웨어를 모름)

### L5: 3D Visualizer
- VTK/PyVista를 PyQt6 QVTKRenderWindowInteractor에 임베딩
- 장비별 3D 모델: 파라메트릭(기본 형상) 또는 CAD 파일(glTF/STL)
- 파트별 독립 교체 가능 (chamber만 CAD, 나머지는 파라메트릭)
- 애니메이션: 턴테이블 회전, 파티클 분사, 로봇 이동, 밸브 색상, 리프터 승강, 배스 액위
- CAD Import: STEP → glTF 변환 → VTK 로딩

### L6: Plugin System
```python
class IPlugin(ABC):
    get_name() -> str
    get_version() -> str
    initialize(config: dict) -> bool
    start() -> None
    stop() -> None
    shutdown() -> None
    set_broker(broker: IMessageBroker) -> None
    get_publish_topics() -> list[str]
    get_subscribe_topics() -> list[str]
    get_widget() -> Optional[QWidget]  # GUI 패널 (없으면 None)
```

플러그인 목록:
- **DB Manager**: sensor_log, alarm_history, process_history 테이블, 배치 INSERT
- **Log Manager**: 카테고리별 파일 분리, 일별 로테이션, 용량 관리
- **Alarm Manager**: alarm.yaml 기반 조건 판정, 인터락 트리거
- **SECS/GEM**: MES 호스트 통신 (선택)

## Settings UI

YAML을 직접 편집하지 않고, GUI에서 시각적으로 설정한다.
Settings UI가 YAML을 자동 생성/저장한다.

### Settings 탭 구성
1. **Equipment**: 장비 타입 (3종), 장비명, 웨이퍼 사이즈, 카세트 용량, 로드포트 수
2. **Baths**: 배스 추가/제거/순서변경, 케미컬 선택 (SPM/SC1/SC2/DHF/BHF/DIW/IPA/ozone/H3PO4), 온도/시간/옵션 설정, Process Flow Preview
3. **I/O Devices**: 밸브/센서/모터/히터 추가/제거, ID/이름/타입/단위 설정
4. **Communication**: PLC 타입 (Siemens/Mitsubishi/Beckhoff/Modbus/None), Transport (TCP/Serial/EtherCAT), 접속 정보, 로봇 컨트롤러 설정
5. **3D Models**: 파트별 Parametric/CAD 선택, CAD 파일 Import (glTF/STL)
6. **Export**: 설정 요약, YAML 미리보기, Save/Launch 버튼

### Chemistry Database
Settings UI의 Bath 탭에서 케미컬을 선택하면 자동으로 물성 데이터가 적용된다:
```yaml
# config/chemistry_db.yaml
chemicals:
  SPM:  { formula: "H2SO4:H2O2=4:1", temp: [100,150], color: "#ff6b35", hazard: high }
  SC1:  { formula: "NH4OH:H2O2:H2O=1:1:5", temp: [60,80], color: "#ab47bc", hazard: med }
  SC2:  { formula: "HCl:H2O2:H2O=1:1:6", temp: [60,80], color: "#42a5f5", hazard: med }
  DHF:  { formula: "HF:H2O=1:100", temp: [20,25], color: "#ffa726", hazard: high }
  BHF:  { formula: "NH4F:HF=6:1", temp: [20,25], color: "#ffb74d", hazard: high }
  DIW:  { formula: "H2O (18.2MΩ·cm)", temp: [20,85], color: "#4fc3f7", hazard: low }
  IPA:  { formula: "C3H8O", temp: [20,82], color: "#fff59d", hazard: med }
  ozone: { formula: "O3/H2O (20-80ppm)", temp: [20,25], color: "#b2ff59", hazard: med }
  H3PO4: { formula: "H3PO4 (85%)", temp: [150,180], color: "#e57373", hazard: high }
```

## YAML Config Examples

### equipment.yaml
```yaml
equipment:
  name: "SAS 6-Bath Immersion Cleaner"
  type: batch_immersion
  wafer_size: 300mm
  loadports: 2
  cassette_slots: 25

communication:
  plc_main:
    transport: { type: tcp, ip: "192.168.1.10", port: 102 }
    protocol: { type: siemens_s7, rack: 0, slot: 1 }
  robot_controller:
    transport: { type: serial, port: COM3, baudrate: 9600 }
    protocol: { type: custom_robot }

baths:
  - id: bath_1
    name: "SC-1"
    chemistry: SC1
    temperature: 70
    dip_time_sec: 600
    megasonic: true
    overflow: true
  - id: bath_2
    name: "QDR-1"
    chemistry: DIW
    temperature: 23
    dip_time_sec: 300
    dump_fill_cycles: 3
  # ... 추가 배스

motors:
  - id: M1
    name: "Transfer Robot"
    channel: robot_controller
    type: servo
    range: [0, 12000]
    max_speed: 500
    io_map:
      command_position: "DB30.DBD0"
      feedback_position: "DB31.DBD0"
      feedback_ready: "DB31.DBX4.0"
  - id: M2
    name: "Lifter"
    channel: plc_main
    type: servo
    range: [-200, 300]
    max_speed: 100

valves:
  - id: V1
    name: "SC1 Supply"
    channel: plc_main
    type: pneumatic
    response_ms: 200
    io_map:
      command: "DB10.DBX0.0"
      feedback_open: "DB11.DBX0.0"
  # ... 추가 밸브

sensors:
  - id: S1
    name: "Bath1 Temperature"
    channel: plc_main
    type: temperature
    unit: "°C"
    range: [15, 85]
    io_map: { value: "DB20.DBD0" }
    simulation: { noise: 0.3, response_tau: 5.0 }
  # ... 추가 센서

heaters:
  - id: H1
    name: "SC1 Heater"
    channel: plc_main
    power_kw: 40
    target_range: [20, 80]
    io_map:
      command_enable: "DB40.DBX0.0"
      command_setpoint: "DB40.DBD2"
      feedback_temperature: "DB41.DBD0"

alarms:
  - id: ALM001
    sensor: S1
    condition: "> 80"
    severity: critical
    interlock: true
  - id: ALM002
    sensor: S2
    condition: "< 2.0"
    severity: warning
    interlock: false

models:
  chamber: { source: parametric, params: { width: 600, depth: 600, height: 800 } }
  loadport: { source: parametric, params: { type: "300mm", ports: 2 } }
  # CAD 적용 시:
  # chamber: { source: cad, file: "models/chamber_v3.glb", scale: 0.001 }
```

## Connected Mode Protocol

외부 GUI 프로그램과 ZeroMQ PUB/SUB으로 통신한다.

### 시뮬레이터 역할
- **SUB** (수신): 외부 GUI의 제어 명령
  - `command/valve/{id}` → `{"action": "open"}` or `{"action": "close"}`
  - `command/motor/{id}` → `{"action": "move", "position": 100.0}`
  - `command/recipe/start` → `{"recipe": "sc1_clean"}`
  - `command/equipment/mode` → `{"mode": "auto"}` or `{"mode": "manual"}`
- **PUB** (발행): 시뮬레이터의 상태 리포트
  - `sensor/{id}/value`, `motor/{id}/position`, `valve/{id}/state`
  - `equipment/state`, `alarm/new`, `recipe/step`

### 핸드셰이크
1. GUI → `system/connect` (접속 요청)
2. SIM → `system/connected` (장비 정보 + I/O 목록 응답)
3. 양방향 `system/heartbeat` (1초 주기)
4. GUI → `system/disconnect` 또는 heartbeat 타임아웃 → 연결 해제

## Fault Injection System

Standalone 모드에서 이상 상황을 인위적으로 발생시켜 알람/인터락 로직을 테스트한다.

### Fault 종류
- **sensor_fail**: 특정 센서 값을 NaN으로 설정 (단선 시뮬레이션)
- **sensor_drift**: 센서 값에 점진적 오프셋 추가 (드리프트)
- **valve_stuck**: 밸브 명령 무시 (고장 시뮬레이션)
- **valve_leak**: 닫힌 밸브에서 미세 유량 발생
- **motor_error**: 모터 이동 명령 거부 (알람 발생)
- **comm_timeout**: 통신 지연/끊김 시뮬레이션
- **e_stop**: 비상 정지 트리거

### GUI
Standalone 모드 우측 패널에 Fault Injection 버튼 그룹 표시.
토글 방식으로 ON/OFF. 활성화 시 해당 디바이스에 빨간색 FAULT 표시.

## Development Phases

### Phase 1: Foundation (W1~W6, 6주)
최소 동작하는 단일 프로세스 시뮬레이터.
- 프로젝트 초기화 (디렉토리, pyproject.toml, requirements.txt)
- ITransport ABC + SimulatorTransport
- IProtocol ABC + SimulatorProtocol
- IMotor, IValve, ISensor, IHeater ABC
- SimulatorHAL (SimMotor, SimValve, SimSensor, SimHeater)
- HAL Manager (YAML → 인스턴스 생성)
- Equipment FSM (상태 머신)
- Recipe Engine (YAML 레시피 파싱 + 순차 실행)
- 기본 GUI (PyQt6 메인 윈도우 + 센서 패널 + START/STOP)
- Batch Spray 기본 레시피 (SC-1, DHF)
- 단위 테스트

### Phase 2: 3D Visualizer (W7~W10, 4주)
3D 시각화 추가.
- VTK/PyVista PyQt6 임베딩
- Batch Spray 3D 모델 (챔버, 턴테이블, 카세트, 노즐, 로봇, 밸브뱅크)
- 파티클 시스템 (스프레이)
- FSM 상태 → 3D 애니메이션 연동
- 카메라 컨트롤 (궤도회전/팬/줌)
- UI 레이아웃 (3D뷰 + 우측 패널)

### Phase 3: Configuration System (W11~W13, 3주)
YAML 기반 동적 구성 + Settings UI.
- 설정 스키마 정의 + 검증
- 설정 로더 (YAML → HAL 인스턴스 자동 생성)
- 동적 GUI 생성 (밸브/센서 패널 자동 구성)
- Settings UI (6탭: Equipment, Baths, I/O, Communication, 3D Models, Export)
- I/O 매핑 시스템
- 프로젝트 전환 (선택 → 설정 로딩 → 씬 재구성)

### Phase 4: Sub-Programs (W14~W18, 5주)
서브 프로그램 분리 + 메시지 브로커.
- ZeroMQ Pub/Sub 브로커
- IPlugin ABC + Plugin Loader
- DB Manager 플러그인
- Log Manager 플러그인
- Alarm Manager 플러그인
- System Launcher (프로세스 관리, 자동 재시작)
- Fault Injection 시스템 + GUI 패널

### Phase 5: Connected Mode (W19~W22, 4주)
외부 GUI 연결.
- Connected Mode 프로토콜 (핸드셰이크, 명령/응답)
- Command Receiver (외부 GUI → 시뮬레이터)
- State Reporter (시뮬레이터 → 외부 GUI)
- 메시지 로그 UI (RX/TX 실시간)
- 테스트용 GUI 클라이언트

### Phase 6: Multi-Equipment + Polish (W23~W26, 4주)
3종 장비 완성.
- Single Spin 3D 모델 + FSM/레시피
- Batch Immersion 3D 모델 + FSM/레시피
- 장비 선택 런처 UI
- CAD Import 파이프라인 (STEP → glTF → VTK)
- UI 폴리싱 + 문서화

## Phase별 Claude Code 시작 명령어

### Phase 1 시작
```
Phase 1을 시작한다. CLAUDE.md를 읽고:
1. 프로젝트 디렉토리 구조를 생성해줘
2. pyproject.toml과 requirements.txt를 작성해줘
3. src/transport/interfaces.py에 ITransport ABC를 정의해줘
4. src/transport/simulator_transport.py에 SimulatorTransport를 구현해줘
```

### Phase 1 다음 단계
```
Phase 1 계속. HAL 인터페이스를 구현한다:
1. src/hal/interfaces.py에 IMotor, IValve, ISensor, IHeater ABC를 정의해줘
2. src/hal/simulator_hal.py에 SimMotor(사다리꼴 가감속), SimValve(응답 지연),
   SimSensor(1차 지연+노이즈), SimHeater(PID 응답)를 구현해줘
3. src/hal/hal_manager.py에 YAML 설정에서 HAL 인스턴스를 생성하는 HALManager를 구현해줘
4. tests/test_hal.py에 단위 테스트를 작성해줘
```
