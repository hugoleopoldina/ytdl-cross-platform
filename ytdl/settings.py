"""Configurações persistentes do usuário (JSON simples, sem dependências).

Arquivo: ``<user_data_dir>/settings.json``.

Chaves avançadas que NÃO têm tela (edite o JSON com o app fechado):

``cookies_file``       Caminho de um cookies.txt (formato Netscape). Ajuda quando o
                       YouTube pede "Confirme que você não é um robô".
``js_runtime_path``    Caminho de deno/node/bun/qjs, se não estiver no PATH.
``ffmpeg_path``        Caminho do ffmpeg, se não estiver no PATH.
``proxy``              Ex.: ``http://127.0.0.1:8080``.
``download_dir``       Pasta de saída (desktop). Vazio = ``Downloads/YTDL``.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Callable, Dict, List

from . import paths
from .logger import get_logger

log = get_logger("settings")

DEFAULTS: Dict[str, Any] = {
    "theme_style": "Dark",       # "Dark" | "Light"
    "primary_palette": "Teal",   # nome de paleta do KivyMD
    "language": "auto",          # "auto" | "pt" | "en"
    "download_dir": "",          # vazio => padrão do sistema
    "max_parallel": 2,           # downloads simultâneos (1..4)
    "search_page_size": 8,       # resultados por página
    "embed_metadata": True,      # grava título/artista/capa nos arquivos
    "last_format": "video",      # "video" | "audio" (pré-seleção do diálogo)
    "cookies_file": "",
    "js_runtime_path": "",
    "ffmpeg_path": "",
    "proxy": "",
}


class Settings:
    """Dicionário com persistência atômica e notificação de mudanças."""

    def __init__(self, path: Any = None) -> None:
        self._path = path or paths.settings_file()
        self._data: Dict[str, Any] = dict(DEFAULTS)
        self._lock = threading.Lock()
        self._listeners: List[Callable[[str, Any], None]] = []
        self.load()

    # -- leitura/escrita ---------------------------------------------------- #
    def load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                stored = json.load(handle)
            if isinstance(stored, dict):
                # Só aceita chaves conhecidas, com o mesmo tipo do padrão.
                for key, default in DEFAULTS.items():
                    if key in stored and isinstance(stored[key], type(default)):
                        self._data[key] = stored[key]
            log.debug("Configurações carregadas de %s", self._path)
        except FileNotFoundError:
            log.info("Sem arquivo de configurações; usando padrões")
        except (OSError, ValueError) as exc:
            log.warning("Configurações inválidas (%s); usando padrões", exc)

    def save(self) -> None:
        tmp = f"{self._path}.tmp"
        try:
            with self._lock:
                with open(tmp, "w", encoding="utf-8") as handle:
                    json.dump(self._data, handle, indent=2, ensure_ascii=False)
                os.replace(tmp, self._path)  # troca atômica
        except OSError as exc:
            log.error("Falha ao salvar configurações: %s", exc)

    def get(self, key: str) -> Any:
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any, *, save: bool = True) -> None:
        if key not in DEFAULTS:
            raise KeyError(f"Configuração desconhecida: {key}")
        if self._data.get(key) == value:
            return
        self._data[key] = value
        log.debug("Configuração %s = %r", key, value)
        if save:
            self.save()
        for listener in list(self._listeners):
            try:
                listener(key, value)
            except Exception:  # noqa: BLE001 - listener não pode derrubar o app
                log.exception("Listener de configuração falhou")

    def add_listener(self, callback: Callable[[str, Any], None]) -> None:
        self._listeners.append(callback)

    # -- atalhos ------------------------------------------------------------ #
    @property
    def output_dir(self) -> str:
        """Pasta onde os downloads são gravados (cria se não existir)."""
        value = self.get("download_dir") or str(paths.default_download_dir())
        os.makedirs(value, exist_ok=True)
        return value
