"""Aplicativo principal (``MDApp``): tema, serviços, navegação e ciclo de vida.

Ordem importante neste arquivo:

1. ``Config.set(...)`` ANTES de importar qualquer coisa que abra a janela
   (``kivy.core.window``); depois disso as opções gráficas são ignoradas.
2. Importar TODOS os widgets/telas em Python antes de carregar os .kv, pois as
   regras ``<MediaCard>:`` etc. só se aplicam a classes já registradas.
3. Carregar os .kv (widgets primeiro, depois telas e shell).
"""
from __future__ import annotations

from typing import List, Optional

from kivy.config import Config

from . import paths

if not paths.is_android():
    # Janela de desktop: tamanho de celular, mas redimensionável (layout responsivo).
    Config.set("graphics", "width", "420")
    Config.set("graphics", "height", "780")
    Config.set("graphics", "minimum_width", "360")
    Config.set("graphics", "minimum_height", "560")
    Config.set("graphics", "resizable", "1")
    # Sem os "pontinhos vermelhos" de multitouch ao clicar com o botão direito.
    Config.set("input", "mouse", "mouse,disable_multitouch")
# Esc/Voltar não fecham o app automaticamente: tratamos em ``_on_keyboard``.
Config.set("kivy", "exit_on_escape", "0")

from kivy.core.window import Window  # noqa: E402
from kivy.lang import Builder  # noqa: E402
from kivy.metrics import dp  # noqa: E402
from kivy.properties import BooleanProperty, NumericProperty, StringProperty  # noqa: E402
from kivymd.app import MDApp  # noqa: E402

from . import APP_NAME, __version__, fonts, i18n, platform_utils  # noqa: E402
from .core import download_manager as dm  # noqa: E402
from .core.errors import UserFacingError  # noqa: E402
from .core.models import MediaItem  # noqa: E402
from .logger import get_logger  # noqa: E402
from .settings import Settings  # noqa: E402
from .ui.common import EmptyState, ui_dispatch  # noqa: E402,F401  (registra EmptyState)
from .ui.screens.detail import DetailScreen  # noqa: E402,F401
from .ui.screens.downloads import DownloadsScreen  # noqa: E402,F401
from .ui.screens.logs import LogsScreen  # noqa: E402,F401
from .ui.screens.search import SearchScreen  # noqa: E402,F401
from .ui.screens.settings import SettingsScreen  # noqa: E402,F401
from .ui.shell import NavItem, Shell  # noqa: E402,F401
from .ui.widgets.download_item import DownloadItem  # noqa: E402,F401
from .ui.widgets.loading_overlay import LoadingOverlay  # noqa: E402
from .ui.widgets.media_card import MediaCard  # noqa: E402,F401
from .ui.widgets.toast import Toast  # noqa: E402

log = get_logger("app")

# Ordem de carregamento dos arquivos .kv (widgets antes das telas que os usam).
KV_FILES = ("widgets.kv", "search.kv", "detail.kv", "downloads.kv", "settings.kv",
            "logs.kv", "shell.kv")
TABS = ("search", "downloads", "settings")


class YtdlApp(MDApp):
    content_font = StringProperty("Roboto")      # fonte ampla p/ títulos (emoji/CJK)
    global_progress = NumericProperty(0.0)        # 0..1, barra fina global
    downloads_active = BooleanProperty(False)

    def __init__(self, demo: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.demo = demo
        self.settings: Optional[Settings] = None
        self.service = None
        self.downloads: Optional[dm.DownloadManager] = None
        self.overlay: Optional[LoadingOverlay] = None
        self._stack: List[str] = ["search"]
        self._syncing_nav = False
        self._last_back = 0.0

    # ------------------------------------------------------------------ build #
    def build(self) -> Shell:
        log.info("Iniciando %s %s (demo=%s, android=%s)", APP_NAME, __version__,
                 self.demo, platform_utils.IS_ANDROID)
        platform_utils.setup_ssl()
        self.settings = Settings()
        i18n.set_language(self.settings.get("language"))

        self.title = APP_NAME
        self.icon = paths.asset("icon.png")
        self.theme_cls.theme_style = self.settings.get("theme_style")
        self.theme_cls.primary_palette = self.settings.get("primary_palette")
        font = fonts.find_content_font()
        if font:
            self.content_font = font

        self._create_services()
        for name in KV_FILES:
            Builder.load_file(paths.kv_file(name))

        self.overlay = LoadingOverlay()
        Window.bind(on_keyboard=self._on_keyboard)
        if not platform_utils.IS_ANDROID:
            Window.minimum_width, Window.minimum_height = 360, 560
        return Shell()

    def _create_services(self) -> None:
        if self.demo:
            from .core.fake_service import FakeService
            self.service = FakeService(self.settings)
            log.info("Modo DEMO: dados fictícios, sem rede")
        else:
            from .core.ytdlp_service import YtdlpService
            self.service = YtdlpService(self.settings)
        self.downloads = dm.DownloadManager(
            self.service, self.settings,
            out_dir=lambda: str(paths.staging_dir()) if platform_utils.IS_ANDROID
            else self.settings.output_dir,
            publisher=None if self.demo else platform_utils.publish_download)
        self.downloads.add_listener(
            lambda event, task: ui_dispatch(lambda: self._on_download_event(event, task)))

    # ------------------------------------------------------------ ciclo de vida #
    def on_start(self) -> None:
        platform_utils.request_storage_permissions()

    def on_pause(self) -> bool:
        return True   # Android: mantém o processo vivo em segundo plano

    def on_stop(self) -> None:
        log.info("Encerrando; cancelando downloads ativos")
        if self.downloads:
            self.downloads.shutdown()

    # --------------------------------------------------------------- helpers UI #
    def tr(self, key: str, **kwargs: object) -> str:
        """Usado nos .kv: ``text: app.tr("download")``."""
        return i18n.tr(key, **kwargs)

    def toast(self, text: str, action_text: str = "", action=None) -> None:  # noqa: ANN001
        """Aviso temporário com ação opcional (ver ``ui/widgets/toast.py``)."""
        Toast(text, action_text, action).show()

    def show_error(self, err: UserFacingError) -> None:
        self.toast(i18n.tr(err.key))

    def show_queued(self, count: int) -> None:
        text = i18n.tr("added_to_queue") if count == 1 else i18n.tr("added_n", n=count)
        self.toast(text, i18n.tr("view"), lambda: self.navigate("downloads"))

    # --------------------------------------------------------------- navegação #
    def navigate(self, name: str) -> None:
        pages = self.root.ids.pages
        if name == pages.current:
            return
        if name in TABS:
            self._stack = [name]
            self._select_tab(name)
        else:
            self._stack.append(name)
        order = {n: i for i, n in enumerate(("search", "downloads", "settings", "detail", "logs"))}
        pages.transition.direction = "left" if order.get(name, 9) > order.get(pages.current, 0) else "right"
        pages.current = name

    def go_back(self) -> bool:
        """Volta uma tela. Retorna False quando já está na raiz."""
        if len(self._stack) <= 1:
            return False
        self._stack.pop()
        pages = self.root.ids.pages
        pages.transition.direction = "right"
        pages.current = self._stack[-1]
        return True

    def open_detail(self, item: MediaItem) -> None:
        self.root.ids.pages.get_screen("detail").open_item(item)
        self.navigate("detail")

    def on_switch_tabs(self, bar, item, item_icon, item_text) -> None:  # noqa: ANN001
        if not self._syncing_nav:
            self.navigate(item.target)

    def _select_tab(self, name: str) -> None:
        """Sincroniza o destaque da barra inferior com a tela atual."""
        bar = self.root.ids.nav
        for item in bar.children:
            if getattr(item, "target", "") == name and not item.active:
                self._syncing_nav = True
                try:
                    bar.set_active_item(item)
                finally:
                    self._syncing_nav = False

    def _on_keyboard(self, window, key, *_args) -> bool:  # noqa: ANN001
        """Tecla Voltar (Android) / Esc (desktop)."""
        if key != 27:
            return False
        if self.go_back():
            return True
        if platform_utils.IS_ANDROID:     # duplo toque para sair
            import time
            now = time.monotonic()
            if now - self._last_back < 2.0:
                self.stop()
            else:
                self._last_back = now
                self.toast(i18n.tr("press_again_exit"))
            return True
        return False

    # ----------------------------------------------------------------- downloads #
    def _on_download_event(self, event: str, task: dm.DownloadTask) -> None:
        self.root.ids.pages.get_screen("downloads").on_event(event, task)
        self.downloads_active = self.downloads.active_count() > 0
        self.global_progress = self.downloads.overall_fraction() or 0.0


def run(demo: bool = False) -> None:
    YtdlApp(demo=demo).run()
