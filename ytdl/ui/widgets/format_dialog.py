"""Diálogo de escolha de formato (áudio/vídeo) antes de baixar."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from kivy.metrics import dp
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivy.uix.widget import Widget
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (MDDialog, MDDialogButtonContainer, MDDialogContentContainer,
                               MDDialogHeadlineText, MDDialogSupportingText)
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import MDListItem
from kivymd.uix.scrollview import MDScrollView

from ...core.formatting import format_bytes
from ...core.models import FormatOption
from ...i18n import tr


class FormatRow(MDListItem):
    """Uma opção selecionável. Aparência em ``widgets.kv`` (<FormatRow>)."""

    icon = StringProperty("music-note")
    headline = StringProperty("")
    supporting = StringProperty("")
    selected = BooleanProperty(False)
    unavailable = BooleanProperty(False)
    option = ObjectProperty(None, allownone=True)


def _describe(option: FormatOption) -> str:
    parts: List[str] = []
    if option.size:
        parts.append(("~" if option.audio_codec else "") + format_bytes(option.size))
    else:
        parts.append(tr("size_unknown"))
    if option.note:
        parts.append(option.note)
    return "  •  ".join(parts)


def open_format_dialog(
    title: str,
    options: List[FormatOption],
    capabilities: Dict[str, bool],
    preferred_media: str,
    on_confirm: Callable[[FormatOption], None],
) -> MDDialog:
    """Abre o diálogo. ``on_confirm`` recebe a opção escolhida."""
    rows: List[FormatRow] = []
    for option in options:
        unavailable = option.needs_ffmpeg and not capabilities.get("ffmpeg", False)
        supporting = _describe(option)
        if unavailable:
            supporting = tr("needs_ffmpeg") + "  •  " + supporting
        rows.append(FormatRow(
            icon="music-note" if option.media == "audio" else "movie-open",
            headline=f"{tr('fmt_audio') if option.media == 'audio' else tr('fmt_video')} · {option.label}",
            supporting=supporting, unavailable=unavailable, option=option))

    state: Dict[str, Optional[FormatRow]] = {"selected": None}

    def select(row: FormatRow) -> None:
        if row.unavailable:
            return
        if state["selected"] is not None:
            state["selected"].selected = False
        row.selected = True
        state["selected"] = row

    for row in rows:
        row.bind(on_release=select)

    # Pré-seleção: respeita o último tipo escolhido (áudio/vídeo).
    available = [r for r in rows if not r.unavailable]
    default = next((r for r in available if r.option.media == preferred_media), None) \
        or (available[0] if available else None)
    if default is not None:
        select(default)

    holder = MDBoxLayout(*rows, orientation="vertical", adaptive_height=True, spacing=dp(4))
    scroller = MDScrollView(holder, size_hint_y=None, height=min(dp(56) * len(rows) + dp(8), dp(300)))

    dialog: MDDialog

    def confirm(*_args: object) -> None:
        chosen = state["selected"]
        if chosen is None:
            return
        dialog.dismiss()
        on_confirm(chosen.option)

    dialog = MDDialog(
        MDDialogHeadlineText(text=tr("choose_format")),
        MDDialogSupportingText(text=title if len(title) < 90 else title[:87] + "…"),
        MDDialogContentContainer(scroller, orientation="vertical"),
        MDDialogButtonContainer(
            Widget(),
            MDButton(MDButtonText(text=tr("cancel")), style="text",
                     on_release=lambda *_: dialog.dismiss()),
            MDButton(MDButtonText(text=tr("download")), style="filled", on_release=confirm),
            spacing=dp(8)),
    )
    dialog.open()
    return dialog
