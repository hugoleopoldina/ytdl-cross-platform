"""Tela de downloads: fila com progresso em tempo real."""
from __future__ import annotations

from typing import Dict

from kivy.app import App
from kivy.properties import BooleanProperty
from kivymd.uix.screen import MDScreen

from ...core import download_manager as dm
from ...i18n import tr
from ..common import EmptyState
from ..widgets.download_item import DownloadItem


class DownloadsScreen(MDScreen):
    empty = BooleanProperty(True)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._items: Dict[int, DownloadItem] = {}

    def on_kv_post(self, base_widget) -> None:  # noqa: ANN001
        self.ids.empty_state.add_widget(EmptyState(
            icon="download-outline", title=tr("downloads_empty"), subtitle=tr("downloads_empty_sub")))

    def on_event(self, event: str, task: dm.DownloadTask) -> None:
        """Chamado na thread da UI para cada evento da fila."""
        box = self.ids.list
        if event == "added":
            widget = DownloadItem(task)
            self._items[task.id] = widget
            box.add_widget(widget, index=0)        # mais recente no topo
        elif event == "removed":
            widget = self._items.pop(task.id, None)
            if widget is not None:
                box.remove_widget(widget)
        else:
            widget = self._items.get(task.id)
            if widget is not None:
                widget.refresh()
        self.empty = not self._items

    def clear_finished(self) -> None:
        App.get_running_app().downloads.clear_finished()
