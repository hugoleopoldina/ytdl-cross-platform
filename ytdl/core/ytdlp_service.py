"""Serviço de mídia baseado em **yt-dlp**.

Substitui, de uma só vez, as três bibliotecas do projeto original que deixaram
de funcionar com o YouTube atual:

=========================  =====================================================
Antes                      Agora
=========================  =====================================================
youtube-search-python      ``ytsearchN:termo`` do yt-dlp (busca)
youtube-search-python      ``extract_info`` (metadados de vídeo/playlist)
pytube                     ``YoutubeDL.extract_info(download=True)``
=========================  =====================================================

Este módulo NÃO importa Kivy. Toda a comunicação com a UI é feita por
callbacks de :class:`~ytdl.core.models.Progress`, o que o torna testável e
permite trocar o backend (ver ``fake_service.py``).

Observações importantes sobre o yt-dlp:

* O ``import yt_dlp`` é feito sob demanda (``_yt``): ele leva ~1 s e não deve
  atrasar a abertura da janela.
* Chamadas de rede do yt-dlp são bloqueantes e não podem ser interrompidas no
  meio. O cancelamento durante *busca/resolução* descarta o resultado; durante
  *download* é imediato (checado a cada evento de progresso).
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..logger import YtdlpLogger, get_logger, traced
from . import system, tagging
from .errors import Cancelled, UserFacingError, classify_exception
from .models import (KIND_LIVE, KIND_PLAYLIST, KIND_SHORT, KIND_VIDEO,
                     FormatOption, MediaItem, Progress, SearchPage)
from .urls import QUERY_PLAYLIST, classify_query
from .worker import CancelToken

log = get_logger("service")

ProgressCallback = Callable[[Progress], None]

# Playlists gigantes travariam a UI; limitamos a lista exibida.
MAX_PLAYLIST_ENTRIES = 300


def _noop(_progress: Progress) -> None:
    pass


# --------------------------------------------------------------------------- #
# Conversão: dicionários do yt-dlp -> modelos do app (funções puras, testáveis)
# --------------------------------------------------------------------------- #
def pick_thumbnail(entry: Dict[str, Any]) -> str:
    """Escolhe uma miniatura JPEG/PNG de bom tamanho (evita WebP e imagens enormes)."""
    candidates = [
        t for t in (entry.get("thumbnails") or [])
        if t.get("url") and t["url"].split("?")[0].lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if candidates:
        sized = [t for t in candidates if (t.get("width") or 0) >= 320]
        if sized:
            return min(sized, key=lambda t: t.get("width") or 0)["url"]
        return candidates[-1]["url"]
    thumb = entry.get("thumbnail") or ""
    if thumb:
        return thumb
    vid = entry.get("id") or ""
    if vid and (entry.get("ie_key") or entry.get("extractor_key") or "").lower().startswith("youtube"):
        return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    return ""


def to_media_item(entry: Dict[str, Any]) -> MediaItem:
    """Converte um dicionário de metadados do yt-dlp em :class:`MediaItem`."""
    vid = str(entry.get("id") or "")
    url = entry.get("webpage_url") or entry.get("url") or ""
    extractor = (entry.get("ie_key") or entry.get("extractor_key") or "").lower()
    if (not url or not url.startswith("http")) and vid and extractor in ("", "youtube"):
        url = f"https://www.youtube.com/watch?v={vid}"

    is_playlist = entry.get("_type") == "playlist" or "playlist?list=" in url
    live_status = entry.get("live_status")
    if is_playlist:
        kind = KIND_PLAYLIST
    elif entry.get("is_live") or live_status in ("is_live", "is_upcoming"):
        kind = KIND_LIVE
    elif "/shorts/" in url:
        kind = KIND_SHORT
    else:
        kind = KIND_VIDEO

    duration = entry.get("duration")
    views = entry.get("view_count")
    count = entry.get("playlist_count") if is_playlist else None
    if is_playlist and count is None and entry.get("entries") is not None:
        count = len(list(entry["entries"]))

    return MediaItem(
        id=vid,
        url=url,
        title=entry.get("title") or entry.get("fulltitle") or url or "(sem título)",
        kind=kind,
        duration=int(duration) if isinstance(duration, (int, float)) else None,
        channel=entry.get("channel") or entry.get("uploader") or entry.get("playlist_uploader") or "",
        views=int(views) if isinstance(views, (int, float)) else None,
        thumbnail=pick_thumbnail(entry),
        count=count,
    )


def _size_of(fmt: Optional[Dict[str, Any]]) -> Optional[int]:
    if not fmt:
        return None
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    return int(size) if size else None


def _has(fmt: Dict[str, Any], key: str) -> bool:
    return (fmt.get(key) or "none") != "none"


def generic_format_options() -> List[FormatOption]:
    """Opções sem tamanho estimado (usadas para playlists inteiras)."""
    return [
        FormatOption("audio_m4a", "audio", "M4A", "m4a",
                     "bestaudio[ext=m4a]/bestaudio/best", note="sem conversão"),
        FormatOption("audio_mp3", "audio", "MP3", "mp3", "bestaudio/best",
                     needs_ffmpeg=True, audio_codec="mp3"),
        FormatOption("video_prog", "video", "MP4 (até 720p)", "mp4",
                     "best[ext=mp4]/best", note="sem conversão"),
        FormatOption("video_1080", "video", "MP4 1080p", "mp4",
                     _merge_selector(1080), needs_ffmpeg=True, merge_to="mp4"),
        FormatOption("video_720", "video", "MP4 720p", "mp4",
                     _merge_selector(720), needs_ffmpeg=True, merge_to="mp4"),
    ]


def _merge_selector(height: int) -> str:
    return (f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]"
            f"/bv*[height<={height}]+ba/b[height<={height}]/b")


def build_format_options(info: Dict[str, Any]) -> List[FormatOption]:
    """Monta as opções de download a partir da lista ``formats`` de um vídeo.

    Tudo que dispensa ffmpeg aparece primeiro; o que precisa dele aparece em
    seguida (a UI desabilita se o ffmpeg não for encontrado).
    """
    formats: List[Dict[str, Any]] = [f for f in (info.get("formats") or []) if f]
    duration = info.get("duration")

    audio_only = [f for f in formats if _has(f, "acodec") and not _has(f, "vcodec")]
    m4a_only = [f for f in audio_only if f.get("ext") == "m4a"]
    best_audio = max(m4a_only or audio_only,
                     key=lambda f: (f.get("abr") or 0, _size_of(f) or 0), default=None)

    progressive = [f for f in formats
                   if _has(f, "vcodec") and _has(f, "acodec") and f.get("ext") == "mp4"]
    best_progressive = max(progressive, key=lambda f: (f.get("height") or 0), default=None)

    video_only = [f for f in formats if _has(f, "vcodec") and not _has(f, "acodec")]

    options: List[FormatOption] = [
        FormatOption("audio_m4a", "audio", "M4A", "m4a",
                     "bestaudio[ext=m4a]/bestaudio/best",
                     size=_size_of(best_audio), note="sem conversão"),
    ]
    if best_progressive is not None:
        height = best_progressive.get("height")
        options.append(FormatOption(
            "video_prog", "video", f"MP4 {height}p" if height else "MP4", "mp4",
            "best[ext=mp4]/best", size=_size_of(best_progressive), note="sem conversão"))

    options.append(FormatOption(
        "audio_mp3", "audio", "MP3", "mp3", "bestaudio/best", needs_ffmpeg=True,
        audio_codec="mp3",
        size=int(duration * 24000) if isinstance(duration, (int, float)) else None,  # ~192 kbps
    ))

    heights = sorted({f["height"] for f in video_only if f.get("height") and f["height"] >= 360},
                     reverse=True)[:4]
    audio_size = _size_of(best_audio) or 0
    for height in heights:
        best_video = max((f for f in video_only if f.get("height") == height),
                         key=lambda f: _size_of(f) or 0)
        video_size = _size_of(best_video)
        options.append(FormatOption(
            f"video_{height}", "video", f"MP4 {height}p", "mp4", _merge_selector(height),
            needs_ffmpeg=True, merge_to="mp4",
            size=(video_size + audio_size) if video_size else None))
    return options


# --------------------------------------------------------------------------- #
# Ponte de progresso do download
# --------------------------------------------------------------------------- #
class _ProgressBridge:
    """Converte os eventos do yt-dlp em :class:`Progress` com fração REAL.

    Um download "vídeo+áudio" baixa DOIS arquivos em sequência. Somamos os
    bytes de todas as partes (pesos pelo tamanho) para a barra não voltar a
    zero quando a segunda parte começa.
    """

    def __init__(self, token: CancelToken, report: ProgressCallback) -> None:
        self._token = token
        self._report = report
        self._parts: Dict[str, List[Optional[int]]] = {}   # id -> [baixado, total]
        self._order: List[str] = []
        self._seeded = False

    def _seed(self, info_dict: Dict[str, Any]) -> None:
        """Pré-carrega os tamanhos esperados de todas as partes do download."""
        if self._seeded:
            return
        self._seeded = True
        for fmt in info_dict.get("requested_formats") or [info_dict]:
            key = str(fmt.get("format_id") or fmt.get("ext") or len(self._order))
            self._parts[key] = [0, _size_of(fmt)]
            self._order.append(key)

    def _overall(self) -> Optional[float]:
        parts = list(self._parts.values())
        if not parts:
            return None
        if all(p[1] for p in parts):  # todos os totais conhecidos: média ponderada
            total = sum(p[1] or 0 for p in parts)
            done = sum(min(p[0] or 0, p[1] or 0) for p in parts)
            return done / total if total else None
        # Algum total desconhecido: média simples por parte.
        fractions = [((p[0] or 0) / p[1]) if p[1] else 0.0 for p in parts]
        return sum(fractions) / len(parts)

    def download_hook(self, data: Dict[str, Any]) -> None:
        self._token.raise_if_cancelled()  # ponto seguro de cancelamento
        info_dict = data.get("info_dict") or {}
        self._seed(info_dict)
        key = str(info_dict.get("format_id") or info_dict.get("ext") or "0")
        if key not in self._parts:
            self._parts[key] = [0, None]
            self._order.append(key)
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            self._parts[key] = [data.get("downloaded_bytes") or 0, int(total) if total else self._parts[key][1]]
            fraction = self._overall()
            self._report(Progress(
                stage="download", fraction=fraction,
                speed=data.get("speed"), eta=data.get("eta"),
                downloaded=data.get("downloaded_bytes"), total_bytes=int(total) if total else None,
                current=len([k for k, p in self._parts.items() if p[1] and p[0] >= p[1]]) + 1,
                total=len(self._parts)))
        elif status == "finished":
            size = data.get("total_bytes") or data.get("downloaded_bytes")
            self._parts[key] = [size, size]
            self._report(Progress(stage="download", fraction=self._overall()))

    def postprocess_hook(self, data: Dict[str, Any]) -> None:
        self._token.raise_if_cancelled()
        name = str(data.get("postprocessor") or "")
        # Só interessa ao usuário o que demora (mesclar/converter). MoveFiles,
        # Metadata etc. são instantâneos e só piscariam a barra.
        slow = any(word in name for word in ("Merger", "Extract", "Convert", "Remux"))
        if slow and data.get("status") in ("started", "processing"):
            # Mesclar/converter não tem porcentagem: barra indeterminada.
            self._report(Progress(stage="postprocess", message=name))


# --------------------------------------------------------------------------- #
# Serviço
# --------------------------------------------------------------------------- #
class DownloadResult:
    def __init__(self, filepath: str, info: Dict[str, Any]) -> None:
        self.filepath = filepath
        self.info = info


class YtdlpService:
    """Fachada sobre o yt-dlp usada pela UI e pelo gerenciador de downloads."""

    def __init__(self, settings: Any) -> None:
        self._settings = settings
        self._yt: Any = None
        self._yt_lock = threading.Lock()
        self._warned = False

    # -- infraestrutura ----------------------------------------------------- #
    @property
    def yt_dlp(self) -> Any:
        """Import tardio e thread-safe do yt_dlp."""
        if self._yt is None:
            with self._yt_lock:
                if self._yt is None:
                    started = time.monotonic()
                    import yt_dlp  # noqa: WPS433 - import tardio proposital
                    self._yt = yt_dlp
                    log.info("yt-dlp %s carregado em %.2fs",
                             getattr(getattr(yt_dlp, "version", None), "__version__", "?"),
                             time.monotonic() - started)
        return self._yt

    def capabilities(self) -> Dict[str, bool]:
        """O que o ambiente atual suporta (a UI usa para habilitar opções)."""
        return {
            "ffmpeg": bool(system.find_ffmpeg(self._settings.get("ffmpeg_path"))),
            "js_runtime": bool(system.find_js_runtime(self._settings.get("js_runtime_path"))),
        }

    def _base_opts(self) -> Dict[str, Any]:
        from .. import paths

        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": False,
            "noprogress": True,
            "logger": YtdlpLogger(),
            "socket_timeout": 20,
            "retries": 3,
            "fragment_retries": 3,
            "extractor_retries": 2,
            "noplaylist": True,
            "cachedir": str(paths.cache_dir()),
            "color": {"stdout": "never", "stderr": "never"},
        }
        proxy = self._settings.get("proxy")
        if proxy:
            opts["proxy"] = proxy
        cookies = self._settings.get("cookies_file")
        if cookies and os.path.isfile(cookies):
            opts["cookiefile"] = cookies

        ffmpeg = system.find_ffmpeg(self._settings.get("ffmpeg_path"))
        if ffmpeg:
            opts["ffmpeg_location"] = ffmpeg

        js = system.find_js_runtime(self._settings.get("js_runtime_path"))
        if js:
            opts["js_runtimes"] = {js[0]: {"path": js[1]}}
        elif not self._warned:
            self._warned = True
            log.warning(
                "Nenhum runtime JavaScript (deno/node/bun/quickjs) encontrado. O yt-dlp pode "
                "não listar todos os formatos do YouTube. Veja a seção 'Runtime JavaScript' do README.")
        return opts

    def _ydl(self, opts: Dict[str, Any]) -> Any:
        return self.yt_dlp.YoutubeDL(opts)

    # -- busca ---------------------------------------------------------------- #
    @traced
    def search(self, query: str, limit: int, offset: int, token: CancelToken,
               report: ProgressCallback = _noop) -> SearchPage:
        """Busca vídeos. ``offset`` permite o botão *Carregar mais*.

        O yt-dlp não tem paginação por cursor na busca: pedimos ``offset+limit``
        resultados e descartamos os já exibidos (a rede entrega em blocos de ~20,
        então o custo extra é pequeno).
        """
        total = offset + limit
        report(Progress(stage="search", message=query))
        opts = self._base_opts()
        opts["extract_flat"] = True            # só metadados leves, sem abrir cada vídeo
        started = time.monotonic()
        with self._ydl(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{total}:{query}", download=False)
        token.raise_if_cancelled()
        entries = [e for e in (info or {}).get("entries") or [] if e]
        log.info("Busca %r: %d resultados em %.2fs", query, len(entries), time.monotonic() - started)
        items = [to_media_item(e) for e in entries[offset:]]
        return SearchPage(items=items, has_more=len(entries) >= total)

    # -- resolução de link ---------------------------------------------------- #
    @traced
    def resolve(self, url: str, token: CancelToken, report: ProgressCallback = _noop) -> MediaItem:
        """Obtém metadados completos de um link (vídeo ou playlist).

        Para vídeos, também preenche ``item.formats`` (opções de download com
        tamanho estimado). Para playlists, preenche ``item.entries``.
        """
        query = classify_query(url)
        is_playlist = query.kind == QUERY_PLAYLIST
        report(Progress(stage="resolve", message=url))
        opts = self._base_opts()
        opts["extract_flat"] = "in_playlist"    # playlist: leve; vídeo único: completo
        opts["noplaylist"] = not is_playlist
        if is_playlist:
            opts["playlistend"] = MAX_PLAYLIST_ENTRIES
        started = time.monotonic()
        with self._ydl(opts) as ydl:
            info = ydl.extract_info(query.text, download=False)
        token.raise_if_cancelled()
        if not info:
            raise UserFacingError("err_unavailable", "extract_info retornou vazio")
        log.info("Resolvido %s (%s) em %.2fs", query.text, info.get("_type", "video"), time.monotonic() - started)

        item = to_media_item(info)
        if item.kind == KIND_PLAYLIST:
            entries = [e for e in (info.get("entries") or []) if e]
            item.entries = [to_media_item(e) for e in entries]
            item.count = len(item.entries)
            item.formats = generic_format_options()
            if not item.thumbnail and item.entries:
                item.thumbnail = item.entries[0].thumbnail
            report(Progress(stage="resolve", fraction=1.0, current=item.count, total=item.count))
        else:
            item.formats = build_format_options(info)
        return item

    # -- download ------------------------------------------------------------- #
    @traced
    def download(self, url: str, option: FormatOption, out_dir: str, token: CancelToken,
                 report: ProgressCallback = _noop) -> DownloadResult:
        """Baixa ``url`` no formato ``option`` para ``out_dir``."""
        caps = self.capabilities()
        if option.needs_ffmpeg and not caps["ffmpeg"]:
            raise UserFacingError("err_ffmpeg", f"{option.key} requer ffmpeg")

        os.makedirs(out_dir, exist_ok=True)
        bridge = _ProgressBridge(token, report)
        opts = self._base_opts()
        opts.update({
            "format": option.selector,
            "paths": {"home": out_dir, "temp": out_dir},
            # Título limitado em BYTES (%B) para não estourar o limite de 255 do sistema
            # de arquivos; o [id] evita colisão entre vídeos de mesmo título.
            "outtmpl": "%(title).120B [%(id)s].%(ext)s",
            "windowsfilenames": True,           # nomes válidos também no Windows/Android
            "overwrites": False,
            "continuedl": True,
            "progress_hooks": [bridge.download_hook],
            "postprocessor_hooks": [bridge.postprocess_hook],
        })
        if option.merge_to:
            opts["merge_output_format"] = option.merge_to
        if option.audio_codec:
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": option.audio_codec,
                "preferredquality": "192",
            }]

        report(Progress(stage="connecting", message=url))
        started = time.monotonic()
        log.info("Baixando %s como %s em %s", url, option.key, out_dir)
        with self._ydl(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        token.raise_if_cancelled()

        filepath = self._final_path(info, out_dir, option)
        log.info("Download concluído em %.1fs: %s", time.monotonic() - started, filepath)

        if self._settings.get("embed_metadata") and filepath:
            report(Progress(stage="tagging"))
            cover = tagging.fetch_cover(tagging.cover_url_for(info))
            tagging.tag_file(filepath, info, cover)
        return DownloadResult(filepath, info)

    @staticmethod
    def _final_path(info: Dict[str, Any], out_dir: str, option: FormatOption) -> str:
        """Descobre o caminho real do arquivo final (após mesclagem/conversão)."""
        downloads = info.get("requested_downloads") or []
        for entry in downloads:
            path = entry.get("filepath") or entry.get("_filename")
            if path and os.path.exists(path):
                return path
        # Fallback: procura pelo id do vídeo na pasta de saída.
        vid = info.get("id") or ""
        if vid:
            matches = [os.path.join(out_dir, n) for n in os.listdir(out_dir) if f"[{vid}]" in n]
            if matches:
                return max(matches, key=os.path.getmtime)
        raise UserFacingError("err_unknown", "arquivo final não encontrado após o download")


__all__ = [
    "YtdlpService", "DownloadResult", "build_format_options", "generic_format_options",
    "to_media_item", "pick_thumbnail", "Cancelled", "classify_exception",
]
