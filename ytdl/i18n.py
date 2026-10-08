"""Textos da interface em português (pt) e inglês (en).

O idioma é detectado automaticamente (sistema operacional) e pode ser forçado
com a variável ``YTDL_LANG=pt|en`` ou na configuração ``language``.
Uso: ``tr("download")`` ou ``tr("selected_n", n=3)``.
"""
from __future__ import annotations

import locale
import os
from typing import Dict

from .logger import get_logger

log = get_logger("i18n")

PT: Dict[str, str] = {
    # navegação
    "nav_search": "Buscar", "nav_downloads": "Downloads", "nav_settings": "Ajustes",
    # busca
    "search_title": "Buscar", "search_hint": "Nome do vídeo ou link",
    "search_empty_title": "Pesquise vídeos ou cole um link",
    "search_empty_sub": "Aceita links de vídeos, shorts e playlists do YouTube e de outros sites.",
    "search_no_results": "Nada encontrado para “{q}”",
    "load_more": "Carregar mais",
    "kind_video": "Vídeo", "kind_short": "Short", "kind_live": "AO VIVO", "kind_playlist": "Playlist",
    "videos_count": "{n} vídeos", "views": "{v} visualizações",
    # carregamento
    "loading_search": "Buscando vídeos…", "loading_resolve": "Lendo informações do link…",
    "loading_building": "Carregando resultados", "loading_connecting": "Conectando…",
    "loading_formats": "Obtendo formatos disponíveis…", "cancel": "Cancelar",
    # detalhes
    "detail_title": "Detalhes", "download": "Baixar", "open_browser": "Abrir no navegador",
    "formats_loading": "Carregando formatos…", "formats_error": "Não foi possível obter os formatos",
    "retry": "Tentar novamente", "choose_format": "Escolha o formato",
    "fmt_audio": "Áudio", "fmt_video": "Vídeo", "needs_ffmpeg": "requer ffmpeg",
    "size_unknown": "tamanho desconhecido", "select_all": "Selecionar tudo",
    "selected_n": "{n} selecionados", "download_selected": "Baixar selecionados",
    "live_unsupported": "Transmissões ao vivo não podem ser baixadas.",
    "added_to_queue": "Adicionado à fila", "added_n": "{n} itens adicionados à fila",
    "view": "Ver", "playlist_truncated": "Mostrando os primeiros {n} vídeos",
    # downloads
    "downloads_title": "Downloads", "downloads_empty": "Nenhum download ainda",
    "downloads_empty_sub": "Os downloads aparecem aqui, com o progresso em tempo real.",
    "clear_finished": "Limpar concluídos",
    "st_queued": "Na fila", "st_running": "Baixando", "st_postprocessing": "Processando arquivo…",
    "st_done": "Concluído", "st_error": "Erro", "st_cancelled": "Cancelado",
    "stage_connecting": "Conectando…", "stage_publishing": "Salvando em Downloads…",
    "stage_tagging": "Gravando metadados…",
    "open_folder": "Abrir pasta", "saved_to": "Salvo em {path}", "remove": "Remover",
    # ajustes
    "settings_title": "Ajustes", "sec_appearance": "Aparência", "dark_theme": "Tema escuro",
    "accent_color": "Cor de destaque", "sec_downloads": "Downloads",
    "parallel": "Downloads simultâneos", "embed_meta": "Gravar título e capa nos arquivos",
    "output_folder": "Pasta de destino", "sec_system": "Sistema",
    "found": "encontrado", "not_found": "não encontrado",
    "ffmpeg_hint": "Sem ffmpeg: somente M4A e MP4 até 720p.",
    "js_hint": "Sem runtime JavaScript alguns formatos do YouTube podem faltar.",
    "view_logs": "Ver logs", "logs_title": "Logs", "refresh": "Atualizar", "copy": "Copiar",
    "copied": "Copiado!", "clear": "Limpar", "app_version": "Versão do app",
    "android_save_hint": "Os arquivos são salvos na pasta Download.",
    "press_again_exit": "Pressione novamente para sair",
    # erros
    "err_network": "Sem conexão ou servidor indisponível.",
    "err_ssl": "Falha na verificação do certificado SSL.",
    "err_private": "Este vídeo é privado ou exclusivo para membros.",
    "err_age": "Este vídeo exige confirmação de idade (veja “cookies” no README).",
    "err_geo": "Este vídeo não está disponível no seu país.",
    "err_unavailable": "Vídeo indisponível ou removido.",
    "err_invalid_url": "Link inválido ou não suportado.",
    "err_ffmpeg": "Este formato precisa do ffmpeg, que não foi encontrado.",
    "err_no_format": "Nenhum formato compatível foi encontrado.",
    "err_rate_limit": "Muitas requisições. Aguarde um pouco e tente de novo.",
    "err_bot_check": "O YouTube pediu verificação anti-robô (veja “cookies” no README).",
    "err_forbidden": "Acesso negado pelo servidor (403). Atualize o yt-dlp.",
    "err_permission": "Sem permissão para gravar na pasta de destino.",
    "err_disk_full": "Sem espaço em disco.",
    "err_unknown": "Erro inesperado. Veja os logs para detalhes.",
}

EN: Dict[str, str] = {
    "nav_search": "Search", "nav_downloads": "Downloads", "nav_settings": "Settings",
    "search_title": "Search", "search_hint": "Video name or link",
    "search_empty_title": "Search videos or paste a link",
    "search_empty_sub": "Accepts video, shorts and playlist links from YouTube and other sites.",
    "search_no_results": "Nothing found for “{q}”",
    "load_more": "Load more",
    "kind_video": "Video", "kind_short": "Short", "kind_live": "LIVE", "kind_playlist": "Playlist",
    "videos_count": "{n} videos", "views": "{v} views",
    "loading_search": "Searching videos…", "loading_resolve": "Reading link information…",
    "loading_building": "Loading results", "loading_connecting": "Connecting…",
    "loading_formats": "Getting available formats…", "cancel": "Cancel",
    "detail_title": "Details", "download": "Download", "open_browser": "Open in browser",
    "formats_loading": "Loading formats…", "formats_error": "Could not get the formats",
    "retry": "Try again", "choose_format": "Choose a format",
    "fmt_audio": "Audio", "fmt_video": "Video", "needs_ffmpeg": "needs ffmpeg",
    "size_unknown": "unknown size", "select_all": "Select all",
    "selected_n": "{n} selected", "download_selected": "Download selected",
    "live_unsupported": "Live streams cannot be downloaded.",
    "added_to_queue": "Added to queue", "added_n": "{n} items added to queue",
    "view": "View", "playlist_truncated": "Showing the first {n} videos",
    "downloads_title": "Downloads", "downloads_empty": "No downloads yet",
    "downloads_empty_sub": "Downloads show up here, with real-time progress.",
    "clear_finished": "Clear finished",
    "st_queued": "Queued", "st_running": "Downloading", "st_postprocessing": "Processing file…",
    "st_done": "Done", "st_error": "Error", "st_cancelled": "Cancelled",
    "stage_connecting": "Connecting…", "stage_publishing": "Saving to Downloads…",
    "stage_tagging": "Writing metadata…",
    "open_folder": "Open folder", "saved_to": "Saved to {path}", "remove": "Remove",
    "settings_title": "Settings", "sec_appearance": "Appearance", "dark_theme": "Dark theme",
    "accent_color": "Accent color", "sec_downloads": "Downloads",
    "parallel": "Simultaneous downloads", "embed_meta": "Write title and cover to files",
    "output_folder": "Output folder", "sec_system": "System",
    "found": "found", "not_found": "not found",
    "ffmpeg_hint": "Without ffmpeg: only M4A and MP4 up to 720p.",
    "js_hint": "Without a JavaScript runtime some YouTube formats may be missing.",
    "view_logs": "View logs", "logs_title": "Logs", "refresh": "Refresh", "copy": "Copy",
    "copied": "Copied!", "clear": "Clear", "app_version": "App version",
    "android_save_hint": "Files are saved to the Download folder.",
    "press_again_exit": "Press again to exit",
    "err_network": "No connection or server unavailable.",
    "err_ssl": "SSL certificate verification failed.",
    "err_private": "This video is private or members-only.",
    "err_age": "This video requires age confirmation (see “cookies” in the README).",
    "err_geo": "This video is not available in your country.",
    "err_unavailable": "Video unavailable or removed.",
    "err_invalid_url": "Invalid or unsupported link.",
    "err_ffmpeg": "This format needs ffmpeg, which was not found.",
    "err_no_format": "No compatible format was found.",
    "err_rate_limit": "Too many requests. Wait a moment and try again.",
    "err_bot_check": "YouTube asked for anti-bot verification (see “cookies” in the README).",
    "err_forbidden": "Access denied by the server (403). Update yt-dlp.",
    "err_permission": "No permission to write to the output folder.",
    "err_disk_full": "No disk space left.",
    "err_unknown": "Unexpected error. See the logs for details.",
}

_TABLES = {"pt": PT, "en": EN}
_current = "en"


def detect_language(preference: str = "auto") -> str:
    """Resolve o idioma efetivo: env > configuração > sistema > inglês."""
    forced = (os.environ.get("YTDL_LANG") or "").lower()[:2]
    if forced in _TABLES:
        return forced
    if preference in _TABLES:
        return preference
    code = ""
    try:  # Android: o ``locale`` do Python costuma não refletir o idioma do aparelho
        from jnius import autoclass  # type: ignore
        code = str(autoclass("java.util.Locale").getDefault().getLanguage())
    except Exception:  # noqa: BLE001 - fora do Android é esperado falhar
        try:
            code = (locale.getdefaultlocale()[0] or "")
        except Exception:  # noqa: BLE001
            code = ""
    return "pt" if code.lower().startswith("pt") else "en"


def set_language(preference: str = "auto") -> str:
    global _current
    _current = detect_language(preference)
    log.info("Idioma da interface: %s", _current)
    return _current


def tr(key: str, **kwargs: object) -> str:
    """Traduz ``key``. Se faltar, cai para inglês e depois para a própria chave."""
    text = _TABLES[_current].get(key) or EN.get(key) or key
    try:
        return text.format(**kwargs) if kwargs else text
    except (KeyError, IndexError):
        log.warning("Texto %r com parâmetros inválidos: %r", key, kwargs)
        return text
