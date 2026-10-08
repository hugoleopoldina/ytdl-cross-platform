"""Classificação do texto digitado: busca, vídeo ou playlist.

O app original usava duas regex gigantes. Aqui usamos ``urllib.parse`` (mais
legível e mais correto) e cobrimos youtu.be, shorts, music.youtube.com etc.
Links de outros sites são aceitos: o yt-dlp suporta milhares de sites.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlparse

QUERY_EMPTY = "empty"
QUERY_SEARCH = "search"
QUERY_VIDEO = "video"
QUERY_PLAYLIST = "playlist"

_YOUTUBE_HOSTS = (
    "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
    "youtube-nocookie.com", "www.youtube-nocookie.com", "youtu.be",
)
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
# Listas geradas automaticamente pelo YouTube (Mix/Rádio): infinitas, tratamos como vídeo.
_AUTO_LIST_PREFIXES = ("RD", "UL")


@dataclass(frozen=True)
class Query:
    kind: str
    text: str                       # texto normalizado (URL ou termo de busca)
    video_id: Optional[str] = None


def _looks_like_url(text: str) -> bool:
    return bool(re.match(r"^(https?://|www\.)\S+$", text, re.IGNORECASE))


def classify_query(raw: str) -> Query:
    """Decide o que fazer com o texto digitado pelo usuário."""
    text = (raw or "").strip()
    if not text:
        return Query(QUERY_EMPTY, "")

    if not _looks_like_url(text):
        return Query(QUERY_SEARCH, text)

    if text.lower().startswith("www."):
        text = "https://" + text
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    params = parse_qs(parsed.query)
    path = parsed.path or ""

    if host not in _YOUTUBE_HOSTS:
        # Outro site: o yt-dlp decide se sabe extrair.
        return Query(QUERY_VIDEO, text)

    video_id: Optional[str] = None
    if host == "youtu.be":
        video_id = path.strip("/").split("/")[0] or None
    elif path.startswith(("/shorts/", "/embed/", "/live/", "/v/")):
        video_id = path.split("/")[2] if len(path.split("/")) > 2 else None
    else:
        video_id = (params.get("v") or [None])[0]
    if video_id and not _VIDEO_ID.match(video_id):
        video_id = None

    playlist_id = (params.get("list") or [None])[0]
    is_playlist_page = path.rstrip("/") == "/playlist"

    if playlist_id and (is_playlist_page or not video_id):
        return Query(QUERY_PLAYLIST, text)
    if playlist_id and video_id and not playlist_id.startswith(_AUTO_LIST_PREFIXES):
        # watch?v=ID&list=PL...: o usuário colou um vídeo DENTRO de uma playlist.
        return Query(QUERY_PLAYLIST, f"https://www.youtube.com/playlist?list={playlist_id}")
    if video_id:
        return Query(QUERY_VIDEO, f"https://www.youtube.com/watch?v={video_id}", video_id)

    # Link do YouTube sem vídeo/playlist (canal, home...): não suportado.
    return Query(QUERY_SEARCH, text)
