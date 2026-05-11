# Wet Process Simulator

반도체 습식 세정장비 제어 소프트웨어 개발을 위한 **3D 시뮬레이션 플랫폼**.

실제 하드웨어 없이 GUI 프로그램, 드라이버, 공정 시퀀스를 검증하는 개발 도구입니다.

---

## 지원 장비 3종

| 장비 | 설명 |
|------|------|
| **Batch Spray** | 턴테이블 + 카세트(25장) + 스프레이 노즐 매니폴드 |
| **Single Wafer Spin** | 스핀 척(최대 3,000 rpm) + 매엽 + 스윙 노즐 암 |
| **Batch Immersion** | 다중 배스(가변) + 리프터 + 카세트 이송 로봇 |

## 운전 모드 2종

| 모드 | 설명 |
|------|------|
| **Standalone** | 내장 FSM + 레시피 엔진으로 공정 자동 실행. Fault Injection 지원 |
| **Connected** | ZeroMQ(PUB/SUB)로 외부 GUI 제어 프로그램과 연결하여 명령 수신/실행 |

---

## 환경 설정

### 요구 사항

- Python 3.11 이상 (권장: MSYS2 ucrt64 환경)
- 의존성 패키지 설치:

```bash
pip install -r requirements.txt
```

### Windows (MSYS2 ucrt64) 추가 설정

VTK OpenGL 렌더링을 위해 `src/main.py` 또는 실행 스크립트에 아래 경로가 등록되어야 합니다:

```python
import os
os.add_dll_directory("C:/msys64/ucrt64/bin")
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
```

이 코드는 `src/visualizer/scene_manager.py` 상단에 이미 포함되어 있습니다.

---

## 실행 방법

### 기본 실행 (런처 화면)

```bash
python -m src.main
```

또는:

```bash
python src/main.py
```

장비 선택 화면이 표시됩니다. 장비 카드를 클릭하고 운전 모드를 선택한 뒤 **시작**을 누릅니다.

### CLI로 직접 실행

```bash
# Batch Spray, Standalone 모드
python -m src.main batch_spray standalone

# Single Spin, Connected 모드
python -m src.main single_spin connected

# Batch Immersion, Standalone 모드
python -m src.main batch_immersion standalone
```

### Connected 모드 테스트 클라이언트

시뮬레이터를 Connected 모드로 실행한 뒤, 별도 터미널에서:

```bash
python -m src.connected.test_client
```

테스트 클라이언트에서 **연결** 버튼을 누르면 ZeroMQ로 시뮬레이터와 연결됩니다.

---

## 주요 기능

### 3D 시각화
- 장비 타입별 파라메트릭 3D 모델 (VTK 기반)
- 카메라 컨트롤: ISO / Front / Top / Reset 뷰 + 마우스 궤도회전/팬/줌
- 애니메이션: 턴테이블 회전, 노즐 암 스윙, 스핀 척 회전
- 파티클 시스템: SC1(보라) / DIW(파란) 스프레이 시각화

### 공정 제어
- FSM 상태 머신: IDLE → INITIALIZING → READY → RUNNING → ABORTING → IDLE
- YAML 레시피 엔진: 밸브/모터/히터/대기 스텝 순차 실행
- 레시피 진행 패널: 현재 스텝 + 전체 진행률 실시간 표시

### HAL 시뮬레이터
- **SimMotor**: 사다리꼴 가감속 (ACCEL → CRUISE → DECEL → DONE)
- **SimValve**: 응답 지연 시뮬레이션 (response_ms)
- **SimSensor**: 1차 지연 응답 + 가우시안 노이즈
- **SimHeater**: PID 응답 근사 (overshoot, settling time)

### Settings UI
- 6탭 설정 다이얼로그 (Equipment / Baths / I/O / Communication / 3D Models / Export)
- YAML 미리보기 + 즉시 저장
- 배스 구성 동적 추가/제거 (Batch Immersion)

### Fault Injection (Standalone)
- Sensor Fail / Sensor Drift / Valve Stuck / Motor Error / Comm Timeout
- 실시간 ON/OFF 토글, 활성 시 빨간 FAULT 표시

### Connected Mode (ZeroMQ)
- 시뮬레이터 PUB: `tcp://127.0.0.1:5555` (상태 리포트)
- 시뮬레이터 SUB: `tcp://127.0.0.1:5556` (명령 수신)
- 핸드셰이크: `system/connect` → `system/connected` (I/O 목록 포함)
- 주기적 heartbeat (1초), 타임아웃 3초 시 자동 연결 해제
- TX(파란)/RX(초록) 색상 구분 메시지 로그

---

## 프로젝트 구조

```
wet-sim-platform/
├── config/
│   ├── chemistry_db.yaml          # 케미컬 물성 DB
│   └── projects/
│       ├── batch_spray/           # 장비별 설정 + 레시피
│       ├── single_spin/
│       └── batch_immersion/
├── src/
│   ├── main.py                    # 엔트리 포인트
│   ├── transport/                 # L1: 물리 전송 (TCP/Serial/Simulator)
│   ├── protocol/                  # L2: PLC 프로토콜 (S7/MC/Modbus/Simulator)
│   ├── hal/                       # L3: 하드웨어 추상화 + 시뮬레이터
│   ├── core/                      # L4: FSM + 레시피 엔진 + Fault Injection
│   ├── visualizer/                # L5: 3D 씬 + 모델 + 애니메이션 + 파티클
│   ├── plugins/                   # L6: DB / Log / Alarm 플러그인
│   ├── broker/                    # ZeroMQ Pub/Sub 브로커
│   ├── connected/                 # Connected Mode (Session/Reporter/Receiver)
│   └── gui/                       # PyQt6 GUI (MainWindow + 패널 + Settings)
├── assets/
│   └── styles/dark_theme.qss     # 다크 테마 스타일시트
└── tests/                         # pytest 단위 테스트 (58개)
```

---

## 설정 파일

각 프로젝트의 `equipment.yaml`에서 I/O 구성을 정의합니다:

```yaml
equipment:
  name: "SAS 6-Bath Immersion Cleaner"
  type: batch_immersion   # batch_spray | single_spin | batch_immersion
  wafer_size: 300mm

baths:                    # batch_immersion만 해당
  - id: bath_1
    name: "SC-1"
    chemistry: SC1
    temperature: 70

motors:
  - id: M1
    name: "Transfer Robot"
    type: servo
    range: [0, 12000]

valves:
  - id: V1
    name: "SC1 Supply"
    type: pneumatic
    response_ms: 200

sensors:
  - id: S1
    name: "Bath1 Temperature"
    type: temperature
    unit: "°C"
    range: [15, 85]
    simulation:
      noise: 0.3
      response_tau: 5.0

heaters:
  - id: H1
    name: "SC1 Heater"
    power_kw: 40.0
    target_range: [20, 80]
```

---

## 개발 환경

| 항목 | 내용 |
|------|------|
| Language | Python 3.11+ |
| GUI | PyQt6 |
| 3D Engine | VTK 9.x (vtkmodules) |
| IPC | ZeroMQ (pyzmq) — PUB/SUB |
| Config | YAML (PyYAML) |
| DB | SQLite |
| Test | pytest (58 tests) |

## 테스트 실행

```bash
pytest tests/ -v
```
