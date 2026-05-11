from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout, QMainWindow, QScrollArea, QStackedWidget,
    QToolBar, QVBoxLayout, QWidget,
)
from PyQt6.QtGui import QAction

from src.config.config_loader import ConfigLoader
from src.connected.session import ConnectedSession
from src.core.equipment_manager import EquipmentManager
from src.core.fsm import EquipmentState
from src.core.fault_injection import FaultInjector
from src.gui.panels.control_panel import ControlPanel
from src.gui.panels.fault_panel import FaultPanel
from src.gui.panels.message_log import MessageLogPanel
from src.gui.panels.sensor_panel import SensorPanel
from src.gui.panels.sequence_panel import SequencePanel
from src.hal.hal_manager import HALManager
from src.visualizer.scene_manager import SceneManager
from src.visualizer.camera_control import CameraControl
from src.visualizer.animation import AnimationManager, RotateAnimation, OscillateAnimation
from src.visualizer.equipment_models.batch_spray import BatchSprayModel
from src.visualizer.equipment_models.single_spin import SingleSpinModel
from src.visualizer.equipment_models.batch_immersion import BatchImmersionModel
from src.visualizer.particles import SprayParticleSystem
from src.gui.settings.settings_window import SettingsWindow


class MainWindow(QMainWindow):
    """메인 윈도우 — 좌측 3D 뷰 + 우측 컨트롤/센서/시퀀스 패널."""

    def __init__(self, project_name: str = "batch_spray",
                 mode: str = "standalone") -> None:
        super().__init__()
        self.setWindowTitle("Wet Process Simulator")
        self.resize(1280, 800)

        self._project_name = project_name
        self._mode = mode
        self._equipment_type: str = "batch_spray"
        self._loader = ConfigLoader()
        self._hal = HALManager()
        self._equipment: EquipmentManager | None = None
        self._recipes: list[dict] = []
        self._session: ConnectedSession | None = None

        self._setup_hal(project_name)
        self._build_ui()
        self._connect_signals()
        self._start_timers()

        if mode == "connected":
            self._start_connected_mode()

    # ── 초기화 ────────────────────────────────────────────────────────────────

    def _setup_hal(self, project_name: str) -> None:
        equipment_cfg = self._loader.load_equipment(project_name)
        self._equipment_type = (equipment_cfg.get("equipment", {})
                                .get("type", "batch_spray"))
        self._hal.load_from_config(equipment_cfg)
        self._recipes = self._loader.load_all_recipes(project_name)
        self._equipment = EquipmentManager(self._hal)
        self._equipment.add_state_listener(self._on_state_change)
        self._equipment.set_step_callback(self._on_step_change)
        self._fault_injector = FaultInjector(self._hal)

    def _build_ui(self) -> None:
        toolbar = QToolBar("Camera", self)
        self.addToolBar(toolbar)
        for label, slot in [
            ("ISO",      lambda: self._camera.set_isometric()),
            ("Front",    lambda: self._camera.set_front()),
            ("Top",      lambda: self._camera.set_top()),
            ("Reset",    lambda: self._camera.reset()),
            ("Settings", lambda: self._open_settings()),
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

        # Standalone: Fault Panel / Connected: Message Log
        self._bottom_stack = QStackedWidget()

        self._fault_panel = FaultPanel()
        self._fault_panel.load_hal(self._hal)
        self._bottom_stack.addWidget(self._fault_panel)   # index 0

        self._msg_log = MessageLogPanel()
        self._bottom_stack.addWidget(self._msg_log)       # index 1

        self._bottom_stack.setMaximumHeight(200)
        self._bottom_stack.setCurrentIndex(0)
        right_layout.addWidget(self._bottom_stack)

        root.addWidget(right_panel, stretch=1)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._scene.Initialize()
        QTimer.singleShot(50, self._init_3d)

    def _init_3d(self) -> None:
        self._scene.GetRenderWindow().Render()
        self._anim_mgr = AnimationManager(self._scene.render)
        self._spray_sc1 = None
        self._spray_diw = None

        if self._equipment_type == "single_spin":
            self._init_3d_single_spin()
        elif self._equipment_type == "batch_immersion":
            self._init_3d_batch_immersion()
        else:
            self._init_3d_batch_spray()

        self._scene.reset_camera()
        self._camera.set_isometric()
        self._scene.render()

    def _init_3d_batch_spray(self) -> None:
        self._eq_model = BatchSprayModel(self._scene)
        self._anim_turntable = RotateAnimation(
            self._eq_model._actor_turntable,
            axis=(0.0, 0.0, 1.0),
            speed_deg_per_sec=36.0,
        )
        self._anim_arm = OscillateAnimation(
            self._eq_model._actor_arm,
            axis=(0.0, 0.0, 1.0),
            amplitude_deg=40.0,
            period_sec=6.0,
        )
        self._anim_mgr.add(self._anim_turntable)
        self._anim_mgr.add(self._anim_arm)

        nozzle_positions = [(-40, y, 483) for y in range(-80, 81, 40)]
        self._spray_sc1 = SprayParticleSystem(
            self._scene, nozzle_positions,
            color=(0.55, 0.2, 0.8),
            actor_name="spray_sc1",
        )
        self._spray_diw = SprayParticleSystem(
            self._scene, nozzle_positions,
            color=(0.3, 0.7, 1.0),
            actor_name="spray_diw",
        )
        self._spray_valve_map = {"spray_sc1": "V1", "spray_diw": "V3"}

    def _init_3d_single_spin(self) -> None:
        self._eq_model = SingleSpinModel(self._scene)
        self._anim_turntable = RotateAnimation(
            self._eq_model._actor_chuck,
            axis=(0.0, 0.0, 1.0),
            speed_deg_per_sec=180.0,
        )
        self._anim_arm = OscillateAnimation(
            self._eq_model._actor_arm,
            axis=(0.0, 0.0, 1.0),
            amplitude_deg=30.0,
            period_sec=8.0,
        )
        self._anim_mgr.add(self._anim_turntable)
        self._anim_mgr.add(self._anim_arm)
        self._spray_valve_map = {}

    def _init_3d_batch_immersion(self) -> None:
        equipment_cfg = self._loader.load_equipment(self._project_name)
        baths = equipment_cfg.get("baths", None)
        self._eq_model = BatchImmersionModel(self._scene, baths=baths)
        self._anim_turntable = OscillateAnimation(
            self._eq_model._actor_lifter_beam,
            axis=(0.0, 0.0, 1.0),
            amplitude_deg=0.0,
            period_sec=4.0,
        )
        self._anim_arm = OscillateAnimation(
            self._eq_model._actor_robot,
            axis=(1.0, 0.0, 0.0),
            amplitude_deg=0.0,
            period_sec=6.0,
        )
        self._anim_mgr.add(self._anim_turntable)
        self._anim_mgr.add(self._anim_arm)
        self._spray_valve_map = {}

    def _connect_signals(self) -> None:
        self._ctrl_panel.sig_init.connect(self._on_init)
        self._ctrl_panel.sig_start.connect(self._on_start)
        self._ctrl_panel.sig_stop.connect(self._on_stop)
        self._ctrl_panel.sig_estop.connect(self._on_estop)

    def _start_timers(self) -> None:
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(100)

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._on_ui_refresh)
        self._ui_timer.start(500)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start(33)

    # ── Connected Mode ────────────────────────────────────────────────────────

    def _start_connected_mode(self) -> None:
        self._session = ConnectedSession(self._hal)
        self._session.on_connect(self._on_zmq_connect)
        self._session.on_disconnect(self._on_zmq_disconnect)
        if self._session.start():
            self._msg_log.set_source(self._session.message_log)
            self._bottom_stack.setCurrentIndex(1)   # 메시지 로그 표시
            self.setWindowTitle(f"Wet Process Simulator — Connected [{self._project_name}]")
        else:
            self._session = None

    def _on_zmq_connect(self) -> None:
        self._msg_log.set_connected(True)

    def _on_zmq_disconnect(self) -> None:
        self._msg_log.set_connected(False)

    def closeEvent(self, event) -> None:
        if self._session:
            self._session.stop()
        super().closeEvent(event)

    # ── 슬롯 ─────────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dlg = SettingsWindow(self._project_name, parent=self)
        dlg.exec()

    def _on_tick(self) -> None:
        if self._equipment:
            self._equipment.tick()
        self._fault_injector.apply()
        if self._session:
            self._session.tick()

    def _on_ui_refresh(self) -> None:
        self._sensor_panel.refresh()
        if self._mode == "connected":
            self._msg_log.refresh()

    def _on_anim_tick(self) -> None:
        if not hasattr(self, "_anim_mgr"):
            return
        self._anim_mgr.tick()
        self._update_particles()

    def _update_particles(self) -> None:
        if not hasattr(self, "_spray_valve_map"):
            return
        spray_map = {
            "spray_sc1": self._spray_sc1,
            "spray_diw": self._spray_diw,
        }
        for name, valve_id in self._spray_valve_map.items():
            spray = spray_map.get(name)
            if spray is None:
                continue
            try:
                is_open = self._hal.get_valve(valve_id).is_open()
            except Exception:
                continue
            if is_open:
                if not spray.is_active:
                    spray.start()
                spray.tick()
            else:
                if spray.is_active:
                    spray.stop()

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
        if self._session and self._session.reporter:
            self._session.reporter.publish_equipment_state(new.name)
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
        if self._session and self._session.reporter:
            self._session.reporter.publish_recipe_step(index, name, total)
