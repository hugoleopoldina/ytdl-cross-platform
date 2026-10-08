"""Utilidades de interface compartilhadas."""
from __future__ import annotations

from typing import Callable

from kivy.clock import Clock
from kivy.properties import StringProperty
from kivymd.uix.boxlayout import MDBoxLayout

from ..core.formatting import clean_display_text, format_count
from ..core.models import MediaItem
from ..i18n import tr


def ui_dispatch(func: Callable[[], None]) -> None:
    """Executa ``func`` na thread principal (única que pode tocar em widgets).

    É a ponte entre as threads de fundo do núcleo e a UI do Kivy.
    """
    Clock.schedule_once(lambda _dt: func(), 0)


def kind_label(kind: str) -> str:
    return tr(f"kind_{kind}")


def media_subtitle(item: MediaItem) -> str:
    """``Canal • 1,2 mi visualizações`` (ou ``Canal • 12 vídeos`` em playlists)."""
    parts = []
    if item.channel:
        parts.append(clean_display_text(item.channel) or item.channel)
    if item.is_playlist and item.count:
        parts.append(tr("videos_count", n=item.count))
    elif item.views is not None:
        parts.append(tr("views", v=format_count(item.views)))
    return "  •  ".join(parts)


class EmptyState(MDBoxLayout):
    """Ícone + título + subtítulo para listas vazias."""

    icon = StringProperty("magnify")
    title = StringProperty("")
    subtitle = StringProperty("")
