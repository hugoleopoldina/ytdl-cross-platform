"""Funções puras de formatação de números e textos."""
from __future__ import annotations

import re
from typing import Optional

_INVALID_FS_CHARS = re.compile(r'[\\/*?:"<>|\x00-\x1f]')
# Emoji (planos suplementares), seletor de variação, ZWJ e keycap. O Kivy não
# renderiza emoji coloridos: sem fonte monocromática eles viram um quadrado.
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\uFE0F\u200D\u20E3\U000E0020-\U000E007F]")


def format_duration(seconds: Optional[float]) -> str:
    """``3725 -> '1:02:05'``; ``65 -> '1:05'``; ``None -> ''``."""
    if seconds is None:
        return ""
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "%d:%02d:%02d" % (hours, minutes, secs)
    return "%d:%02d" % (minutes, secs)


def format_count(value: Optional[int]) -> str:
    """Contagem compacta: ``1234 -> '1,2 mil'``, ``2_500_000 -> '2,5 mi'``."""
    if value is None:
        return ""
    for limit, suffix in ((1_000_000_000, " bi"), (1_000_000, " mi"), (1_000, " mil")):
        if value >= limit:
            number = value / limit
            text = ("%.1f" % number).rstrip("0").rstrip(".") if number < 100 else "%d" % number
            return text.replace(".", ",") + suffix
    return str(value)


def format_bytes(size: Optional[float]) -> str:
    """``1536 -> '1,5 KB'``; ``None -> '?'``."""
    if size is None:
        return "?"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return "%d B" % value
            return ("%.1f %s" % (value, unit)).replace(".", ",")
        value /= 1024
    return "?"  # pragma: no cover


def format_speed(bytes_per_second: Optional[float]) -> str:
    if not bytes_per_second:
        return ""
    return format_bytes(bytes_per_second) + "/s"


def format_eta(seconds: Optional[int]) -> str:
    if seconds is None:
        return ""
    return format_duration(seconds)


def sanitize_filename(name: str, max_length: int = 150) -> str:
    """Remove caracteres inválidos em Windows/Linux/Android e limita o tamanho."""
    cleaned = _INVALID_FS_CHARS.sub("_", name).strip(" .")
    return (cleaned or "download")[:max_length]


def clean_display_text(text: str) -> str:
    """Remove emoji do texto EXIBIDO (nomes de arquivo e tags não são afetados)."""
    return re.sub(r"\s+", " ", _EMOJI.sub("", text or "")).strip()
