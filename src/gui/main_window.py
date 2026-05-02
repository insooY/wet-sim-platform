from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout, QMainWindow, QScrollArea, QToolBar, QVBoxLayout, QWidget
)
from PyQt6.QtGui import QAction

from src.config.config_loader import ConfigLoader
from src.core.equipment_manager import EquipmentManager
from src.core.fsm import EquipmentState
from src.gui.panels.control_panel import ControlPanel
from src.gui.panels.sensor_panel import SensorPanel
from src.gui.panels.sequence_panel import SequencePanel
from src.hal.hal_manager import HALManager
from src.visualizer.scene_manager import SceneManager
from src.visualizer.camera_control import CameraControl
from src.visualizer.animation import AnimationManager, RotateAnimation, OscillateAnimation
from src.visualizer.equipment_models.batch_spray import BatchSprayModel
from src.visualizer.particles import SprayParticleSystem


class MainWindow(QMainWindow):
    """메인 윈도우 — 좌측 3D 뷰 + 우측 컨트롤/센서/시퀀스 패널."""

    def __init__(self, project_name: str = "batch_spray") -> None:
        super().__init__()
        self.setWindowTitle("Wet Process Simulator")
        self.resize(1280, 800)

        self._loader = ConfigLoader()
        self._hal = HALManager()
        self._equipment: EquipmentManager | None = None
        self._recipes: list[dict] = []

        self._setup_hal(project_name)
        self._build_ui()
        self._connect_signals()
        self._start_timers()

    # ── 초기화 ────────────────────────────────────────────────────────────────

    def _setup_hal(self, project_name: str) -> None:
        equipment_cfg = self._loader.load_equipment(project_name)
        self._hal.load_from_config(equipment_cfg)
        self._recipes = self._loader.load_all_recipes(project_name)
        self._equipment = EquipmentManager(self._hal)
        self._equipment.add_state_listener(self._on_state_change)
        self._equipment.set_step_callback(self._on_step_change)

    def _build_ui(self) -> None:
        # 카메라 뷰 툴바
        toolbar = QToolBar("Camera", self)
        self.addToolBar(toolbar)
        for label, slot in [
            ("ISO",   lambda: self._camera.set_isometric()),
            ("Front", lambda: self._camera.set_front()),
            ("Top",   lambda: self._camera.set_top()),
            ("Reset", lambda: self._camera.reset()),
        ]:
            action = QAction(label, self)
            action.triggered.connect(slot)
            toolbar.addAction(action)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # 좌측 — VTK 3D 뷰
        self._scene = SceneManager()
        self._scene.setMinimumWidth(800)
        self._camera = CameraControl(self._scene.renderer)
        root.addWidget(self._scene, stretch=3)

        # 우측 패널
        right_panel = QWidget()
        right_panel.setFixedWidth(300)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self._ctrl_panel = ControlPanel()
        self._ctrl_panel.set_recipes([r["recipe"]["name"] for r in self._recipes])
        right_layout.addWidget(self._ctrl_panel)

        self._seq_panel = SequencePanel()
        right_layout.addWidget(self._seq_panel)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._sensor_panel = SensorPanel()
        self._sensor_panel.load_hal(self._hal)
        scroll.setWidget(self._sensor_panel)
        right_layout.addWidget(scroll, stretch=1)

        root.addWidget(right_panel, stretch=1)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(100, self._init_3d)

    def _init_3d(self) -> None:
        self._scene.initialize()
        self._eq_model = BatchSprayModel(self._scene)
        self._anim_mgr = AnimationManager(self._scene.render)
        self._anim_turntable = RotateAnimation(
            self._eq_model._actor_turntable,
            axis=(0.0, 0.0, 1.0),
            speed_deg_per_sec=36.0,   # 1 rpm
        )
        self._anim_arm = OscillateAnimation(
            self._eq_model._actor_arm,
            axis=(0.0, 0.0, 1.0),
            amplitude_deg=40.0,
            period_sec=6.0,
        )
        self._anim_mgr.add(self._anim_turntable)
        self._anim_mgr.add(self._anim_arm)

        # 노즐 팁 위치 (batch_spray 모델과 동일 좌표)
        nozzle_positions = [(-40, y, 483) for y in range(-80, 81, 40)]
        self._spray_sc1 = SprayParticleSystem(
            self._scene, nozzle_positions,
            color=(0.55, 0.2, 0.8),   # SC1 보라색
            actor_name="spray_sc1",
        )
        self._spray_diw = SprayParticleSystem(
            self._scene, nozzle_positions,
            color=(0.3, 0.7, 1.0),    # DIW 파란색
            actor_name="spray_diw",
        )
        self._scene.reset_camera()
        self._camera.set_isometric()

    def _connect_signals(self) -> None:
        self._ctrl_panel.sig_init.connect(self._on_init)
        self._ctrl_panel.sig_start.connect(self._on_start)
        self._ctrl_panel.sig_stop.connect(self._on_stop)
        self._ctrl_panel.sig_estop.connect(self._on_estop)

    def _start_timers(self) -> None:
        # 장비 tick (100 ms)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(100)

        # UI 갱신 (500 ms)
        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._sensor_panel.refresh)
        self._ui_timer.start(500)

        # 3D 애니메이션 tick (33 ms ≈ 30 fps)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start(33)

    # ── 슬롯 ─────────────────────────────────────────────────────────────────

    def _on_tick(self) -> None:
        if self._equipment:
            self._equipment.tick()

    def _on_anim_tick(self) -> None:
        if not hasattr(self, "_anim_mgr"):
            return
        self._anim_mgr.tick()
        self._update_particles()

    def _update_particles(self) -> None:
        """밸브 상태에 따라 파티클 시작/중지 및 tick."""
        if not hasattr(self, "_spray_sc1"):
            return
        v1_open = self._hal.get_valve("V1").is_open()
        v3_open = self._hal.get_valve("V3").is_open()

        if v1_open:
            if not self._spray_sc1.is_active:
                self._spray_sc1.start()
            self._spray_sc1.tick()
        else:
            if self._spray_sc1.is_active:
                self._spray_sc1.stop()

        if v3_open:
            if not self._spray_diw.is_active:
                self._spray_diw.start()
            self._spray_diw.tick()
        else:
            if self._spray_diw.is_active:
                self._spray_diw.stop()

    def _on_init(self) -> None:
        if self._equipment:
            self._equipment.initialize()

    def _on_start(self, recipe_name: str) -> None:
        if not self._equipment:
            return
        recipe = next((r for r in self._recipes if r["recipe"]["name"] == recipe_name), None)
        if recipe:
            self._seq_panel.set_recipe_name(recipe_name)
            self._equipment.start_recipe(recipe["recipe"] if "recipe" in recipe else recipe)

    def _on_stop(self) -> None:
        if self._equipment:
            self._equipment.abort()
            self._seq_panel.reset()

    def _on_estop(self) -> None:
        if self._equipment:
            self._equipment.emergency_stop()
            self._seq_panel.reset()

    def _on_state_change(self, old: EquipmentState, new: EquipmentState) -> None:
        self._ctrl_panel.update_state(new)
        if not hasattr(self, "_anim_turntable"):
            return
        if new == EquipmentState.RUNNING:
            self._anim_turntable.start()
            self._anim_arm.start()
        else:
            self._anim_turntable.stop()
            self._anim_arm.stop()

    def _on_step_change(self, index: int, name: str) -> None:
        current, total = self._equipment.recipe_progress
        self._seq_panel.update_progress(current, total, name)
