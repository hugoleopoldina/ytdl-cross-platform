"""Linha da lista de downloads com progresso em tempo real."""
from __future__ import annotations

from kivy.app import App
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivymd.uix.card import MDCard

from ...core import download_manager as dm
from ...core.formatting import format_bytes, format_eta, format_speed
from ...i18n import tr
from ... import platform_utils


class DownloadItem(MDCard):
    task = ObjectProperty(None, allownone=True)
    title = StringProperty("")
    thumbnail = StringProperty("")
    status_text = StringProperty("")
    status_color = ListProperty([0.5, 0.5, 0.5, 1])
    value = NumericProperty(0)                 # 0..100
    indeterminate = BooleanProperty(False)
    show_bar = BooleanProperty(True)
    primary_icon = StringProperty("close")
    primary_enabled = BooleanProperty(True)
    can_remove = BooleanProperty(False)

    def __init__(self, task: dm.DownloadTask, **kwargs) -> None:
        super().__init__(**kwargs)
        self.task = task
        self.title = task.item.display_title
        self.thumbnail = task.item.thumbnail
        self.refresh()

    def refresh(self) -> None:
        """Recalcula tudo o que a linha mostra a partir do estado da tarefa."""
        task = self.task
        theme = App.get_running_app().theme_cls
        muted, error, ok = theme.onSurfaceVariantColor, theme.errorColor, theme.primaryColor
        p = task.progress
        state = task.state
        self.status_color = muted
        self.can_remove = state in dm.FINISHED_STATES
        self.show_bar = state in dm.ACTIVE_STATES

        if state == dm.QUEUED:
            self.status_text = tr("st_queued")
            self.indeterminate, self.primary_icon, self.primary_enabled = True, "close", True
        elif state == dm.POSTPROCESSING or p.stage in ("tagging", "publishing"):
            key = "stage_tagging" if p.stage == "tagging" else (
                "stage_publishing" if p.stage == "publishing" else "st_postprocessing")
            self.status_text = tr(key)
            self.indeterminate, self.primary_icon, self.primary_enabled = True, "close", p.stage != "publishing"
        elif state == dm.RUNNING:
            if p.fraction is None or p.stage == "connecting":
                self.status_text = tr("stage_connecting")
                self.indeterminate = True
            else:
                self.indeterminate = False
                self.value = p.fraction * 100
                parts = ["%d%%" % round(p.fraction * 100)]
                if p.downloaded and p.total_bytes:
                    parts.append(f"{format_bytes(p.downloaded)} / {format_bytes(p.total_bytes)}")
                if p.speed:
                    parts.append(format_speed(p.speed))
                if p.eta is not None:
                    parts.append(format_eta(p.eta))
                self.status_text = "  •  ".join(parts)
            self.primary_icon, self.primary_enabled = "close", True
        elif state == dm.DONE:
            self.status_text = tr("saved_to", path=task.location)
            self.status_color = ok
            self.primary_icon = "folder-open-outline" if not platform_utils.IS_ANDROID else "check-circle-outline"
            self.primary_enabled = not platform_utils.IS_ANDROID
        elif state == dm.ERROR:
            self.status_text = f"{tr('st_error')}: {tr(task.error_key or 'err_unknown')}"
            self.status_color = error
            self.primary_icon, self.primary_enabled = "refresh", True
        elif state == dm.CANCELLED:
            self.status_text = tr("st_cancelled")
            self.primary_icon, self.primary_enabled = "refresh", True

    def on_primary(self) -> None:
        """Botão principal: cancelar / repetir / abrir pasta, conforme o estado."""
        app = App.get_running_app()
        state = self.task.state
        if state in dm.ACTIVE_STATES:
            app.downloads.cancel(self.task)
        elif state in (dm.ERROR, dm.CANCELLED):
            app.downloads.retry(self.task)
        elif state == dm.DONE:
            platform_utils.open_folder(self.task.filepath)

    def on_remove(self) -> None:
        App.get_running_app().downloads.remove(self.task)
