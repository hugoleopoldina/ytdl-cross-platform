"""Tela de ajustes: aparência, downloads e informações do sistema."""
from __future__ import annotations

from typing import Dict

from kivy.app import App
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.utils import get_color_from_hex, hex_colormap
from kivymd.uix.button import MDIconButton
from kivymd.uix.screen import MDScreen

from ... import platform_utils
from ... import __version__
from ...core import system
from ...i18n import tr

PALETTES = ("Teal", "Blue", "Indigo", "Purple", "Pink", "Red", "Orange", "Green")


def _palette_rgba(name: str):
    """KivyMD 2.x gera o esquema M3 a partir de uma cor CSS (``hex_colormap``)."""
    return list(get_color_from_hex(hex_colormap[name.lower()]))


class SettingsScreen(MDScreen):
    dark = BooleanProperty(True)
    embed_meta = BooleanProperty(True)
    parallel = NumericProperty(2)
    palette = StringProperty("Teal")
    output_text = StringProperty("")
    ffmpeg_text = StringProperty("")
    js_text = StringProperty("")
    ytdlp_text = StringProperty("")
    app_text = StringProperty("")
    is_android = BooleanProperty(platform_utils.IS_ANDROID)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._swatches: Dict[str, MDIconButton] = {}

    def on_kv_post(self, base_widget) -> None:  # noqa: ANN001
        for name in PALETTES:
            button = MDIconButton(
                icon="circle", style="standard", theme_icon_color="Custom",
                icon_color=_palette_rgba(name), size_hint=(None, None),
                size=(dp(40), dp(40)))
            button.bind(on_release=lambda _b, n=name: self.set_palette(n))
            self._swatches[name] = button
            self.ids.swatches.add_widget(button)

    def on_pre_enter(self, *_args: object) -> None:
        app = App.get_running_app()
        s = app.settings
        self.dark = s.get("theme_style") == "Dark"
        self.embed_meta = bool(s.get("embed_metadata"))
        self.parallel = int(s.get("max_parallel"))
        self.palette = s.get("primary_palette")
        self._mark_palette()
        self.output_text = tr("android_save_hint") if platform_utils.IS_ANDROID else s.output_dir
        info = system.system_info(s)
        self.ffmpeg_text = info["ffmpeg"] or tr("not_found")
        self.js_text = info["js_runtime"] or tr("not_found")
        self.ytdlp_text = info["yt_dlp"]
        self.app_text = f"{__version__}  •  Python {info['python']}"

    def _mark_palette(self) -> None:
        for name, button in self._swatches.items():
            button.icon = "check-circle" if name == self.palette else "circle"

    # -- handlers ------------------------------------------------------------- #
    def set_dark(self, value: bool) -> None:
        self.dark = value
        app = App.get_running_app()
        app.settings.set("theme_style", "Dark" if value else "Light")
        app.theme_cls.theme_style = "Dark" if value else "Light"

    def set_palette(self, name: str) -> None:
        self.palette = name
        self._mark_palette()
        app = App.get_running_app()
        app.settings.set("primary_palette", name)
        app.theme_cls.primary_palette = name

    def set_embed(self, value: bool) -> None:
        self.embed_meta = value
        App.get_running_app().settings.set("embed_metadata", value)

    def change_parallel(self, delta: int) -> None:
        self.parallel = max(1, min(4, int(self.parallel) + delta))
        App.get_running_app().settings.set("max_parallel", int(self.parallel))

    def open_output(self) -> None:
        platform_utils.open_folder(App.get_running_app().settings.output_dir)
