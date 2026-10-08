"""Tela de logs: mostra o arquivo de log dentro do app (ótimo para depurar no celular)."""
from __future__ import annotations

from kivy.core.clipboard import Clipboard
from kivy.properties import StringProperty
from kivymd.uix.screen import MDScreen

from ... import logger
from ...i18n import tr
from kivy.app import App


class LogsScreen(MDScreen):
    text = StringProperty("")

    def on_pre_enter(self, *_args: object) -> None:
        self.refresh()

    def refresh(self) -> None:
        lines = logger.tail_log(120)
        # Limita o tamanho: texturas do Kivy têm tamanho máximo.
        self.text = "\n".join(line[:220] for line in lines) or "(vazio)"

    def copy(self) -> None:
        Clipboard.copy("\n".join(logger.tail_log(400)))
        App.get_running_app().toast(tr("copied"))

    def clear(self) -> None:
        logger.clear_log()
        self.refresh()
