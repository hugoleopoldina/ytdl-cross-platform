"""Configuração central de logging.

Tudo no aplicativo registra mensagens com ``get_logger(__name__)``. Os logs vão
para três lugares:

1. **Console** (stderr) - em desenvolvimento e no ``logcat`` do Android
   (``adb logcat -s python``).
2. **Arquivo rotativo** ``<user_data_dir>/logs/ytdl.log`` (3 x 1 MB), também
   exibido dentro do app na tela *Configurações > Ver logs*.
3. Mensagens do **yt-dlp** são redirecionadas para o mesmo destino através de
   :class:`YtdlpLogger`, em vez de poluir o stdout.

Como aumentar o detalhamento:

* ``python main.py --debug``
* ou variável de ambiente ``YTDL_LOG_LEVEL=DEBUG``
"""
from __future__ import annotations

import functools
import logging
import logging.handlers
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, List, Optional, TypeVar

from . import paths

ROOT_NAME = "ytdl"
LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s"
DATE_FORMAT = "%H:%M:%S"

_configured = False
_log_file: Optional[Path] = None


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger filho de ``ytdl`` (``ytdl.core.service`` etc.)."""
    if name == ROOT_NAME or name.startswith(ROOT_NAME + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{ROOT_NAME}.{name}")


def log_file_path() -> Optional[Path]:
    return _log_file


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """Configura o logger raiz do app. Seguro chamar mais de uma vez."""
    global _configured, _log_file
    root = logging.getLogger(ROOT_NAME)
    if _configured:
        if level:
            root.setLevel(level.upper())
        return root

    level_name = (level or os.environ.get("YTDL_LOG_LEVEL") or "INFO").upper()
    root.setLevel(level_name)
    # O Kivy altera o logging global; não propagamos para evitar duplicatas.
    root.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # Em apps "windowed" do PyInstaller sys.stderr é None: não há console.
    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        root.addHandler(console)

    try:
        _log_file = paths.logs_dir() / "ytdl.log"
        file_handler = logging.handlers.RotatingFileHandler(
            _log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as exc:  # disco cheio / sem permissão: segue só com console
        root.warning("Não foi possível criar o arquivo de log: %s", exc)
        _log_file = None

    _install_exception_hooks(root)
    _configured = True
    root.info("Logging iniciado (nível=%s, arquivo=%s)", level_name, _log_file)
    return root


def _install_exception_hooks(root: logging.Logger) -> None:
    """Registra exceções não tratadas (inclusive de threads) no log."""
    previous = sys.excepthook

    def excepthook(exc_type, exc, tb):  # type: ignore[no-untyped-def]
        root.critical("Exceção não tratada", exc_info=(exc_type, exc, tb))
        previous(exc_type, exc, tb)

    sys.excepthook = excepthook

    if hasattr(threading, "excepthook"):  # Python 3.8+
        def thread_hook(args):  # type: ignore[no-untyped-def]
            root.critical(
                "Exceção não tratada na thread %s",
                getattr(args.thread, "name", "?"),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        threading.excepthook = thread_hook


def tail_log(max_lines: int = 150) -> List[str]:
    """Últimas linhas do arquivo de log (para a tela de logs)."""
    if not _log_file or not _log_file.exists():
        return []
    try:
        with open(_log_file, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().splitlines()[-max_lines:]
    except OSError:
        return []


def clear_log() -> None:
    if _log_file and _log_file.exists():
        try:
            open(_log_file, "w", encoding="utf-8").close()
        except OSError:
            pass


F = TypeVar("F", bound=Callable[..., Any])


def traced(func: F) -> F:
    """Decorador de diagnóstico: registra entrada, saída, duração e falhas.

    Só emite mensagens em nível DEBUG, então não custa nada em produção.
    """
    log = get_logger(f"trace.{func.__module__.rsplit('.', 1)[-1]}")

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not log.isEnabledFor(logging.DEBUG):
            return func(*args, **kwargs)
        started = time.monotonic()
        log.debug("-> %s", func.__qualname__)
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            log.debug("!! %s falhou após %.2fs: %r", func.__qualname__,
                      time.monotonic() - started, exc)
            raise
        log.debug("<- %s (%.2fs)", func.__qualname__, time.monotonic() - started)
        return result

    return wrapper  # type: ignore[return-value]


class YtdlpLogger:
    """Adaptador: o yt-dlp aceita um objeto com debug/info/warning/error."""

    def __init__(self) -> None:
        self._log = get_logger("yt_dlp")

    def debug(self, msg: str) -> None:
        # O yt-dlp envia mensagens informativas por debug() prefixadas.
        if msg.startswith("[debug] "):
            self._log.debug(msg[8:])
        else:
            self._log.info(msg)

    def info(self, msg: str) -> None:
        self._log.info(msg)

    def warning(self, msg: str) -> None:
        self._log.warning(msg)

    def error(self, msg: str) -> None:
        self._log.error(msg)
