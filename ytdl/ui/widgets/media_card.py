"""Cartão de resultado de busca (miniatura + título + canal)."""
from __future__ import annotations

from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivymd.uix.card import MDCard

from ...core.formatting import format_duration
from ...core.models import KIND_LIVE, KIND_VIDEO, MediaItem
from ..common import kind_label, media_subtitle


class MediaCard(MDCard):
    """A aparência está em ``ui/kv/widgets.kv`` (<MediaCard>)."""

    item = ObjectProperty(None, allownone=True)
    thumbnail = StringProperty("")
    title = StringProperty("")
    subtitle = StringProperty("")
    duration_text = StringProperty("")
    kind_text = StringProperty("")
    show_kind = BooleanProperty(False)
    is_live = BooleanProperty(False)

    def __init__(self, item: MediaItem, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_item(item)

    def set_item(self, item: MediaItem) -> None:
        self.item = item
        self.thumbnail = item.thumbnail
        self.title = item.display_title
        self.subtitle = media_subtitle(item)
        self.duration_text = format_duration(item.duration) if item.duration else ""
        self.is_live = item.kind == KIND_LIVE
        self.show_kind = item.kind != KIND_VIDEO
        self.kind_text = kind_label(item.kind)
