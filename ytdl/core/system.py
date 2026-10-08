"""Detecção de ferramentas externas e informações do ambiente.

* **ffmpeg** - necessário para MP3 e para vídeos acima de 720p (junta
  vídeo+áudio). Opcional: sem ele o app baixa M4A e MP4 progressivo.
* **Runtime JavaScript** (deno/node/bun/quickjs) - desde nov/2025 o yt-dlp
  precisa de um para resolver os desafios do YouTube; sem ele alguns formatos
  somem. Veja https://github.com/yt-dlp/yt-dlp/wiki/EJS
"""
from __future__ import annotations

import os
import platform
import shutil
import sys
from typing import Dict, Optional, Tuple

from ..logger import get_logger

log = get_logger("system")

_EXE = ".exe" if sys.platform.startswith("win") else ""
# Ordem de preferência do yt-dlp: deno é o padrão recomendado.
JS_RUNTIMES = ("deno", "node", "bun", "qjs")
# Nome do runtime no yt-dlp para cada executável.
_JS_NAMES = {"deno": "deno", "node": "node", "bun": "bun", "qjs": "quickjs"}


def _bundled_dirs() -> Tuple[str, ...]:
    """Pastas onde um binário pode ser distribuído junto ao app (só se empacotado)."""
    dirs = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(meipass)
    if getattr(sys, "frozen", False):
        dirs.append(os.path.dirname(sys.executable))
    # Nunca procuramos no diretório atual (cwd): no Windows isso permitiria executar
    # um ffmpeg.exe plantado numa pasta qualquer.
    return tuple(dirs)


def _find_binary(name: str, explicit: str = "") -> Optional[str]:
    """Procura um executável: caminho configurado > ao lado do app > PATH."""
    if explicit and os.path.isfile(explicit):
        return explicit
    for base in _bundled_dirs():
        for sub in ("", "bin", "ffmpeg"):
            candidate = os.path.join(base, sub, name + _EXE)
            if os.path.isfile(candidate):
                return candidate
    return shutil.which(name)


def find_ffmpeg(explicit: str = "") -> Optional[str]:
    return _find_binary("ffmpeg", explicit)


def find_js_runtime(explicit: str = "") -> Optional[Tuple[str, str]]:
    """Retorna ``(nome_no_yt_dlp, caminho)`` do primeiro runtime encontrado."""
    if explicit and os.path.isfile(explicit):
        stem = os.path.splitext(os.path.basename(explicit))[0].lower()
        return _JS_NAMES.get(stem, "deno"), explicit
    for exe in JS_RUNTIMES:
        found = _find_binary(exe)
        if found:
            return _JS_NAMES[exe], found
    return None


def ytdlp_version() -> str:
    try:
        from yt_dlp.version import __version__  # import leve
        return __version__
    except Exception:  # noqa: BLE001
        return "não instalado"


def system_info(settings: Optional[object] = None) -> Dict[str, str]:
    """Dicionário legível para a tela de configurações e para os logs."""
    get = getattr(settings, "get", lambda _k: "")
    ffmpeg = find_ffmpeg(get("ffmpeg_path") or "")
    js = find_js_runtime(get("js_runtime_path") or "")
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "yt_dlp": ytdlp_version(),
        "ffmpeg": ffmpeg or "",
        "js_runtime": f"{js[0]} ({js[1]})" if js else "",
    }
