"""Aviso temporário (substitui o ``MDSnackbar``).

Por que não usar o ``MDSnackbar`` do KivyMD 2.0.0?  Ele é criado com altura
adaptativa igual a ZERO, e o ripple do ``MDCard`` cria um framebuffer (FBO) com
o tamanho do widget. Drivers Mesa (Linux, inclusive GPUs reais) rejeitam FBO de
tamanho zero e o app quebra com ``FBO Initialization failed: Incomplete
attachment``. Este ``Toast`` nasce com tamanho explícito e não tem esse problema.
"""
from __future__ import annotations

from typing import Callable, Optional

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

_current: Optional["Toast"] = None


class Toast(MDCard):
    def __init__(self, text: str, action_text: str = "",
                 action: Optional[Callable[[], None]] = None, **kwargs) -> None:
        width = min(Window.width - dp(24), dp(520))
        theme = MDApp.get_running_app().theme_cls
        super().__init__(
            style="filled", size_hint=(None, None), size=(width, dp(52)),
            padding=(dp(16), 0, dp(8), 0), radius=[dp(8)], ripple_behavior=False,
            theme_bg_color="Custom", md_bg_color=theme.inverseSurfaceColor, **kwargs)
        label = MDLabel(text=text, font_style="Body", role="medium", max_lines=2,
                        theme_text_color="Custom", text_color=theme.inverseOnSurfaceColor)
        self.add_widget(label)
        if action_text and action:
            self.add_widget(MDButton(
                MDButtonText(text=action_text, theme_text_color="Custom",
                             text_color=theme.inversePrimaryColor),
                style="text", size_hint_x=None, pos_hint={"center_y": .5},
                on_release=lambda *_: (action(), self.dismiss())))
        self._timer = None

    def show(self, duration: float = 3.0) -> None:
        global _current
        if _current is not None:
            _current.dismiss(animate=False)
        _current = self
        self.pos = ((Window.width - self.width) / 2, dp(88))
        self.opacity = 0
        Window.add_widget(self)
        Animation(opacity=1, duration=0.18).start(self)
        self._timer = Clock.schedule_once(lambda _dt: self.dismiss(), duration)

    def dismiss(self, animate: bool = True) -> None:
        global _current
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if _current is self:
            _current = None
        if self.parent is None:
            return
        if not animate:
            Window.remove_widget(self)
            return
        anim = Animation(opacity=0, duration=0.2)
        anim.bind(on_complete=lambda *_: self.parent and Window.remove_widget(self))
        anim.start(self)
