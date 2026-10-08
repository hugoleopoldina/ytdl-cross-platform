"""Modelos de dados do núcleo (dataclasses simples, sem Kivy).

Mantê-los independentes da UI permite testar a lógica sem abrir janela e
trocar o backend (ex.: ``FakeService`` do modo ``--demo``) sem tocar na UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Tipos de mídia exibidos na UI
KIND_VIDEO = "video"
KIND_SHORT = "short"
KIND_LIVE = "live"
KIND_PLAYLIST = "playlist"


@dataclass
class MediaItem:
    """Um vídeo, short, live ou playlist (resultado de busca ou link colado)."""

    id: str
    url: str
    title: str
    kind: str = KIND_VIDEO
    duration: Optional[int] = None        # segundos; None em lives/playlists
    channel: str = ""
    views: Optional[int] = None
    thumbnail: str = ""
    count: Optional[int] = None           # nº de vídeos (playlists)
    entries: List["MediaItem"] = field(default_factory=list)  # itens da playlist
    # Preenchido por ``resolve``: formatos disponíveis para download
    formats: List["FormatOption"] = field(default_factory=list)

    @property
    def display_title(self) -> str:
        """Título para a tela (sem emoji, que o Kivy não consegue desenhar)."""
        from .formatting import clean_display_text
        return clean_display_text(self.title) or self.title

    @property
    def is_playlist(self) -> bool:
        return self.kind == KIND_PLAYLIST

    @property
    def downloadable(self) -> bool:
        # Lives em andamento não podem ser baixadas por este app.
        return self.kind != KIND_LIVE


@dataclass
class FormatOption:
    """Uma opção de download mostrada ao usuário (áudio MP3, vídeo 720p...)."""

    key: str                      # identificador estável: "audio_m4a", "video_1080"...
    media: str                    # "audio" | "video"
    label: str                    # texto curto: "MP4 1080p"
    ext: str                      # extensão final esperada
    selector: str                 # seletor de formato do yt-dlp (-f)
    needs_ffmpeg: bool = False
    audio_codec: Optional[str] = None   # "mp3" => FFmpegExtractAudio
    merge_to: Optional[str] = None      # "mp4" => merge_output_format
    size: Optional[int] = None          # bytes estimados (None = desconhecido)
    note: str = ""                      # observação curta (ex.: "sem conversão")


@dataclass
class Progress:
    """Evento de progresso genérico (busca, resolução ou download).

    ``fraction=None`` significa *indeterminado*: a UI mostra a barra animada.
    Quando o total é conhecido, ``fraction`` vai de 0.0 a 1.0 e é REAL (bytes
    baixados / bytes totais, vídeos carregados / vídeos totais...), nunca um
    contador de tempo fixo como no app original.
    """

    stage: str                             # "connecting" | "search" | "download" | ...
    message: str = ""
    fraction: Optional[float] = None
    current: Optional[int] = None
    total: Optional[int] = None
    speed: Optional[float] = None          # bytes/s
    eta: Optional[int] = None              # segundos
    downloaded: Optional[int] = None       # bytes
    total_bytes: Optional[int] = None


@dataclass
class SearchPage:
    items: List[MediaItem]
    has_more: bool = False
