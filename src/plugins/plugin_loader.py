"""플러그인 동적 로더 — config에서 플러그인 목록을 읽어 인스턴스를 생성한다."""
from __future__ import annotations

import importlib
import logging
from typing import Any

from src.broker.message_broker import IMessageBroker
from src.plugins.plugin_interface import IPlugin

log = logging.getLogger(__name__)


class PluginLoader:
    """YAML 설정 또는 명시적 등록으로 플러그인을 관리한다."""

    def __init__(self, broker: IMessageBroker) -> None:
        self._broker = broker
        self._plugins: list[IPlugin] = []

    # ── 등록 ─────────────────────────────────────────────────────────────────

    def register(self, plugin: IPlugin, config: dict[str, Any] | None = None) -> bool:
        """플러그인 인스턴스를 직접 등록한다."""
        plugin.set_broker(self._broker)
        if not plugin.initialize(config or {}):
            log.warning("플러그인 초기화 실패: %s", plugin.get_name())
            return False
        self._plugins.append(plugin)
        log.info("플러그인 등록: %s v%s", plugin.get_name(), plugin.get_version())
        return True

    def load_from_config(self, plugins_cfg: list[dict[str, Any]]) -> None:
        """YAML plugins 섹션에서 플러그인을 동적으로 로드한다.

        각 항목 형식:
          - module: src.plugins.db_manager.db_plugin
            class:  DBPlugin
            config: { ... }
        """
        for entry in plugins_cfg:
            module_path = entry.get("module", "")
            class_name = entry.get("class", "")
            config = entry.get("config", {})
            if not module_path or not class_name:
                log.warning("플러그인 설정 누락 — module/class 필드가 없습니다: %s", entry)
                continue
            try:
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                plugin: IPlugin = cls()
                self.register(plugin, config)
            except Exception as e:
                log.error("플러그인 로드 실패 (%s.%s): %s", module_path, class_name, e)

    # ── 생명주기 ──────────────────────────────────────────────────────────────

    def start_all(self) -> None:
        for p in self._plugins:
            try:
                p.start()
                log.info("플러그인 시작: %s", p.get_name())
            except Exception as e:
                log.error("플러그인 시작 오류 (%s): %s", p.get_name(), e)

    def stop_all(self) -> None:
        for p in reversed(self._plugins):
            try:
                p.stop()
            except Exception as e:
                log.error("플러그인 정지 오류 (%s): %s", p.get_name(), e)

    def shutdown_all(self) -> None:
        for p in reversed(self._plugins):
            try:
                p.shutdown()
            except Exception as e:
                log.error("플러그인 종료 오류 (%s): %s", p.get_name(), e)
        self._plugins.clear()

    # ── 조회 ─────────────────────────────────────────────────────────────────

    def get_all(self) -> list[IPlugin]:
        return list(self._plugins)

    def get_by_name(self, name: str) -> IPlugin | None:
        return next((p for p in self._plugins if p.get_name() == name), None)
