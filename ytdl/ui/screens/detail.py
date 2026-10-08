"""Tela de detalhes: miniatura, informações, formatos e (se playlist) seus vídeos."""
from __future__ import annotations

from typing import List, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import (BooleanProperty, NumericProperty, ObjectProperty, StringProperty)
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.screen import MDScreen

from ... import platform_utils
from ...core.errors import UserFacingError
from ...core.formatting import format_duration
from ...core.models import KIND_LIVE, MediaItem
from ...core.worker import CancelToken, run_background
from ...i18n import tr
from ...logger import get_logger
from ..common import kind_label, media_subtitle, ui_dispatch
from ..widgets.format_dialog import open_format_dialog

log = get_logger("ui.detail")

ROW_BATCH = 12   # linhas de playlist criadas por quadro


class EntryRow(MDBoxLayout):
    """Linha de um vídeo dentro de uma playlist (com caixa de seleção)."""

    item = ObjectProperty(None, allownone=True)
    selected = BooleanProperty(True)
    title = StringProperty("")
    meta = StringProperty("")
    thumbnail = StringProperty("")

    def __init__(self, item: MediaItem, **kwargs) -> None:
        super().__init__(**kwargs)
        self.item = item
        self.title = item.display_title
        self.thumbnail = item.thumbnail
        self.meta = "  •  ".join(p for p in (format_duration(item.duration) if item.duration else "", item.channel) if p)


class DetailScreen(MDScreen):
    item = ObjectProperty(None, allownone=True)
    thumbnail = StringProperty("")
    title = StringProperty("")
    subtitle = StringProperty("")
    duration_text = StringProperty("")
    kind_text = StringProperty("")
    show_kind = BooleanProperty(False)
    is_live = BooleanProperty(False)
    is_playlist = BooleanProperty(False)
    loading = BooleanProperty(False)          # buscando formatos/entradas
    failed = BooleanProperty(False)
    build_fraction = NumericProperty(-1)      # <0: indeterminado
    selected_count = NumericProperty(0)
    can_download = BooleanProperty(False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._token: Optional[CancelToken] = None
        self._rows: List[EntryRow] = []
        self._build_event = None

    # -- abrir um item ------------------------------------------------------- #
    def open_item(self, item: MediaItem) -> None:
        self._reset()
        self.item = item
        self.thumbnail = item.thumbnail
        self.title = item.display_title
        self.subtitle = media_subtitle(item)
        self.duration_text = format_duration(item.duration) if item.duration else ""
        self.is_live = item.kind == KIND_LIVE
        self.is_playlist = item.is_playlist
        self.kind_text = kind_label(item.kind)
        self.show_kind = item.kind != "video"
        if item.is_playlist and item.entries:
            self._build_rows(item.entries)
        if (item.is_playlist and not item.entries) or (not item.is_playlist and not item.formats):
            self.fetch()
        self._update_can_download()

    def _reset(self) -> None:
        if self._token:
            self._token.cancel()
        if self._build_event:
            self._build_event.cancel()
        self._token = self._build_event = None
        self.ids.entries_box.clear_widgets()
        self._rows = []
        self.loading = self.failed = False
        self.selected_count = 0
        self.build_fraction = -1

    def fetch(self) -> None:
        """Obtém formatos (vídeo) ou a lista de vídeos (playlist) em segundo plano."""
        app = App.get_running_app()
        item = self.item
        if item is None:
            return
        token = self._token = CancelToken()
        self.loading, self.failed, self.build_fraction = True, False, -1
        log.info("Buscando detalhes de %s", item.url)

        def done(full: MediaItem) -> None:
            if self._token is not token:
                return
            item.formats = full.formats
            item.entries = full.entries
            item.count = full.count or item.count
            item.duration = item.duration or full.duration
            if full.thumbnail and not item.thumbnail:
                item.thumbnail = self.thumbnail = full.thumbnail
            self.subtitle = media_subtitle(item)
            self.duration_text = format_duration(item.duration) if item.duration else ""
            if item.is_playlist:
                self._build_rows(item.entries)
            else:
                self.loading = False
            self._update_can_download()

        def fail(err: UserFacingError) -> None:
            if self._token is token:
                self.loading, self.failed = False, True
                app.show_error(err)

        run_background(lambda: app.service.resolve(item.url, token), done, fail,
                       ui_dispatch, token)

    # -- playlist --------------------------------------------------------------- #
    def _build_rows(self, entries: List[MediaItem]) -> None:
        """Monta as linhas aos poucos; a barra mostra linhas criadas / total."""
        box = self.ids.entries_box
        total, built = len(entries), 0
        self.loading, self.build_fraction = True, 0.0

        def step(_dt: float) -> bool:
            nonlocal built
            for entry in entries[built:built + ROW_BATCH]:
                row = EntryRow(entry)
                row.bind(selected=lambda *_: self._update_selected())
                self._rows.append(row)
                box.add_widget(row)
            built = min(built + ROW_BATCH, total)
            self.build_fraction = built / total if total else 1.0
            if built >= total:
                self._build_event = None
                self.loading = False
                self._update_selected()
                return False
            return True

        if total == 0:
            self.loading = False
            return
        self._build_event = Clock.schedule_interval(step, 0)

    def _update_selected(self) -> None:
        self.selected_count = sum(1 for r in self._rows if r.selected)
        self._update_can_download()

    def toggle_all(self) -> None:
        value = self.selected_count < len(self._rows)
        for row in self._rows:
            row.selected = value

    def _update_can_download(self) -> None:
        if self.item is None or self.is_live:
            self.can_download = False
        elif self.is_playlist:
            self.can_download = self.selected_count > 0 and bool(self.item.formats)
        else:
            self.can_download = bool(self.item.formats)

    # -- ações -------------------------------------------------------------------- #
    def on_download(self) -> None:
        app = App.get_running_app()
        item = self.item
        if item is None or not item.formats:
            return
        targets = [r.item for r in self._rows if r.selected] if self.is_playlist else [item]

        def confirm(option) -> None:  # noqa: ANN001
            app.settings.set("last_format", option.media)
            for target in targets:
                app.downloads.enqueue(target, option)
            app.show_queued(len(targets))

        open_format_dialog(item.display_title, item.formats, app.service.capabilities(),
                           app.settings.get("last_format"), confirm)

    def open_in_browser(self) -> None:
        if self.item and self.item.url.startswith("http"):
            platform_utils.open_url(self.item.url)
