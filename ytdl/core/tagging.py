"""Gravação de metadados (título, artista, capa) nos arquivos baixados.

Usa apenas ``mutagen`` (Python puro): funciona no Android sem ffmpeg.
O app original tentava gravar tags MP4 e depois **renomeava** o arquivo para
``.mp3`` - o que gerava arquivos M4A com extensão errada. Aqui cada formato
recebe as tags corretas e MP3 só existe quando o ffmpeg converte de verdade.

Falhas aqui NUNCA devem quebrar um download: o arquivo já está pronto.
"""
from __future__ import annotations

import os
import ssl
import urllib.request
from typing import Any, Dict, Optional

from ..logger import get_logger

log = get_logger("tagging")


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        return ssl.create_default_context()


def fetch_cover(url: str, timeout: int = 15) -> Optional[bytes]:
    """Baixa a capa (JPEG/PNG). Retorna None em qualquer falha."""
    if not url:
        return None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as resp:
            data = resp.read(5_000_000)
        if data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n":
            return data
        log.debug("Capa em formato não suportado (%s); ignorando", url)
    except Exception as exc:  # noqa: BLE001
        log.warning("Não foi possível baixar a capa: %s", exc)
    return None


def cover_url_for(info: Dict[str, Any]) -> str:
    """Prefere o JPEG padrão do YouTube (o ``thumbnail`` costuma ser WebP)."""
    video_id = info.get("id") or ""
    if (info.get("extractor_key") or "").lower().startswith("youtube") and video_id:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    thumb = info.get("thumbnail") or ""
    return thumb if thumb.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png")) else ""


def tag_file(path: str, info: Dict[str, Any], cover: Optional[bytes]) -> bool:
    """Grava tags conforme a extensão. Retorna True se gravou algo."""
    ext = os.path.splitext(path)[1].lower()
    title = info.get("title") or ""
    artist = info.get("artist") or info.get("creator") or info.get("uploader") or info.get("channel") or ""
    try:
        if ext in (".m4a", ".mp4", ".m4v"):
            return _tag_mp4(path, title, artist, cover)
        if ext == ".mp3":
            return _tag_mp3(path, title, artist, cover)
        log.debug("Sem suporte a tags para %s; pulando", ext)
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao gravar tags em %s: %s", os.path.basename(path), exc)
    return False


def _tag_mp4(path: str, title: str, artist: str, cover: Optional[bytes]) -> bool:
    from mutagen.mp4 import MP4, MP4Cover

    audio = MP4(path)
    if audio.tags is None:
        audio.add_tags()
    if title:
        audio["\xa9nam"] = [title]
    if artist:
        audio["\xa9ART"] = [artist]
    if cover:
        fmt = MP4Cover.FORMAT_PNG if cover[:4] == b"\x89PNG" else MP4Cover.FORMAT_JPEG
        audio["covr"] = [MP4Cover(cover, imageformat=fmt)]
    audio.save()
    return True


def _tag_mp3(path: str, title: str, artist: str, cover: Optional[bytes]) -> bool:
    from mutagen.id3 import APIC, ID3, ID3NoHeaderError, TIT2, TPE1

    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    if title:
        tags.add(TIT2(encoding=3, text=title))
    if artist:
        tags.add(TPE1(encoding=3, text=artist))
    if cover:
        mime = "image/png" if cover[:4] == b"\x89PNG" else "image/jpeg"
        tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=cover))
    tags.save(path)
    return True
