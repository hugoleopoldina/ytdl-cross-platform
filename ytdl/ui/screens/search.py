"""Tela de busca: campo + resultados com carregamento progressivo."""
from __future__ import annotations

from typing import List, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import BooleanProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.screen import MDScreen

from ...core.errors import UserFacingError
from ...core.models import MediaItem, Progress, SearchPage
from ...core.urls import QUERY_EMPTY, QUERY_SEARCH, Query, classify_query
from ...core.worker import CancelToken, run_background
from ...i18n import tr
from ...logger import get_logger
from ..common import EmptyState, ui_dispatch
from ..widgets.media_card import MediaCard

log = get_logger("ui.search")

BUILD_BATCH = 2   # cartões criados por quadro: mantém a UI fluida e a barra real


class SearchScreen(MDScreen):
    has_more = BooleanProperty(False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._token: Optional[CancelToken] = None
        self._query = ""
        self._offset = 0
        self._build_event = None
        self._footer: Optional[MDBoxLayout] = None

    def on_kv_post(self, base_widget) -> None:  # noqa: ANN001
        self._show_empty()

    # -- estados vazios ------------------------------------------------------ #
    def _show_empty(self, icon: str = "magnify", title: str = "", subtitle: str = "") -> None:
        box = self.ids.results
        box.clear_widgets()
        box.add_widget(EmptyState(
            icon=icon, title=title or tr("search_empty_title"),
            subtitle=subtitle if title else tr("search_empty_sub")))

    # -- ações do usuário ---------------------------------------------------- #
    def do_search(self) -> None:
        query = classify_query(self.ids.field.text)
        if query.kind == QUERY_EMPTY:
            return
        self._abort()
        self.ids.field.focus = False
        if query.kind == QUERY_SEARCH:
            self._query, self._offset = query.text, 0
            self._run_search(replace=True)
        else:
            self._run_resolve(query)

    def load_more(self) -> None:
        self._abort()
        self._run_search(replace=False)

    def _abort(self) -> None:
        if self._token:
            self._token.cancel()
            self._token = None
        if self._build_event:
            self._build_event.cancel()
            self._build_event = None
        App.get_running_app().overlay.close()

    # -- busca ---------------------------------------------------------------- #
    def _run_search(self, replace: bool) -> None:
        app = App.get_running_app()
        token = self._token = CancelToken()
        overlay = app.overlay
        overlay.show(tr("loading_search"), on_cancel=token.cancel)
        limit = int(app.settings.get("search_page_size"))
        offset = 0 if replace else self._offset
        log.info("Buscando %r (offset=%d, limite=%d)", self._query, offset, limit)

        def report(progress: Progress) -> None:
            if self._token is token:
                ui_dispatch(lambda: overlay.update(progress) if self._token is token else None)

        run_background(
            lambda: app.service.search(self._query, limit, offset, token, report),
            on_done=lambda page: self._on_search_done(page, replace, token),
            on_error=lambda err: self._on_error(err, replace),
            dispatch=ui_dispatch, token=token)

    def _on_search_done(self, page: SearchPage, replace: bool, token: CancelToken) -> None:
        if self._token is not token:
            return
        if replace:
            self.ids.results.clear_widgets()
            self._footer = None
            self._offset = 0
        self._offset += len(page.items)
        self.has_more = page.has_more
        if not page.items and replace:
            App.get_running_app().overlay.close()
            self._show_empty("magnify-close", tr("search_no_results", q=self._query))
            return
        self._build_cards(list(page.items))

    def _build_cards(self, items: List[MediaItem]) -> None:
        """Cria os cartões aos poucos; a barra do overlay mostra o andamento REAL."""
        overlay = App.get_running_app().overlay
        box = self.ids.results
        if self._footer is not None and self._footer.parent is box:
            box.remove_widget(self._footer)
        total, built = len(items), 0
        overlay.set_progress(0.0, f"0 / {total}", title=tr("loading_building"))

        def step(_dt: float) -> bool:
            nonlocal built
            for item in items[built:built + BUILD_BATCH]:
                card = MediaCard(item)
                card.bind(on_release=lambda c: App.get_running_app().open_detail(c.item))
                box.add_widget(card)
            built = min(built + BUILD_BATCH, total)
            overlay.set_progress(built / total, f"{built} / {total}")
            if built >= total:
                self._build_event = None
                self._add_footer()
                Clock.schedule_once(lambda _d: overlay.close(), 0.15)
                return False
            return True

        self._build_event = Clock.schedule_interval(step, 0)

    def _add_footer(self) -> None:
        if not self.has_more:
            return
        if self._footer is None:
            button = MDButton(MDButtonText(text=tr("load_more")), style="tonal",
                              pos_hint={"center_x": .5}, on_release=lambda *_: self.load_more())
            self._footer = MDBoxLayout(button, size_hint_y=None, height=dp(72), padding=dp(12))
        self.ids.results.add_widget(self._footer)

    # -- link colado ---------------------------------------------------------- #
    def _run_resolve(self, query: Query) -> None:
        app = App.get_running_app()
        token = self._token = CancelToken()
        overlay = app.overlay
        overlay.show(tr("loading_resolve"), on_cancel=token.cancel)
        log.info("Resolvendo link %s", query.text)

        def done(item: MediaItem) -> None:
            overlay.close()
            app.open_detail(item)

        run_background(
            lambda: app.service.resolve(query.text, token),
            on_done=done, on_error=lambda err: self._on_error(err, False),
            dispatch=ui_dispatch, token=token)

    def _on_error(self, err: UserFacingError, replace: bool) -> None:
        app = App.get_running_app()
        app.overlay.close()
        # Sem resultados na tela: mostra o erro no próprio estado vazio (além do aviso).
        if not any(isinstance(child, MediaCard) for child in self.ids.results.children):
            self._show_empty("alert-circle-outline", tr(err.key))
        app.show_error(err)
