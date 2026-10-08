"""Resolução de caminhos para todos os ambientes de execução.

O projeto original precisava de uma CÓPIA da pasta ``src`` (a pasta ``build/``)
com caminhos alterados para funcionar com o PyInstaller. Aqui isso é resolvido
em um único lugar: toda busca por arquivos (assets, .kv) passa por este módulo,
que sabe onde os arquivos estão em cada cenário:

==============  ==========================================================
Cenário         Onde ficam os arquivos
==============  ==========================================================
Desenvolvimento  <raiz do projeto>/ytdl/...
PyInstaller      sys._MEIPASS/ytdl/...   (pasta temporária ou _internal/)
Android (APK)    <ANDROID_APP_PATH>/ytdl/...  (extraído pelo p4a)
==============  ==========================================================

Este módulo NÃO importa Kivy de propósito: ele precisa funcionar antes da
inicialização da janela (o logging, por exemplo, depende dele).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

APP_DIRNAME = "YTDL"


# --------------------------------------------------------------------------- #
# Detecção de ambiente
# --------------------------------------------------------------------------- #
def is_frozen() -> bool:
    """True quando rodando dentro de um executável do PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def is_android() -> bool:
    """True quando rodando dentro de um APK gerado pelo python-for-android.

    O p4a exporta estas variáveis de ambiente antes de iniciar o Python. Usar
    variáveis evita importar ``kivy.utils.platform`` (que importaria o Kivy).
    """
    return "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ


def is_windows() -> bool:
    return sys.platform.startswith("win")


# --------------------------------------------------------------------------- #
# Arquivos empacotados (somente leitura)
# --------------------------------------------------------------------------- #
def _base_dir() -> Path:
    """Diretório que CONTÉM a pasta ``ytdl``."""
    meipass = getattr(sys, "_MEIPASS", None)  # definido pelo PyInstaller
    if meipass:
        return Path(meipass)
    # paths.py está em <raiz>/ytdl/paths.py  ->  parent.parent == <raiz>
    return Path(__file__).resolve().parent.parent


def package_dir() -> Path:
    return _base_dir() / "ytdl"


def asset(*parts: str) -> str:
    """Caminho (str) de um arquivo em ``ytdl/assets``. Kivy exige ``str``."""
    return str(package_dir().joinpath("assets", *parts))


def kv_file(name: str) -> str:
    """Caminho (str) de um arquivo .kv em ``ytdl/ui/kv``."""
    return str(package_dir().joinpath("ui", "kv", name))


# --------------------------------------------------------------------------- #
# Diretórios graváveis
# --------------------------------------------------------------------------- #
def user_data_dir() -> Path:
    """Pasta privada do app (configurações, logs, cache). Sempre gravável."""
    if is_android():
        # Mesma pasta que ``App.user_data_dir`` retorna no Android.
        base = os.environ.get("ANDROID_PRIVATE") or os.environ.get("ANDROID_APP_PATH")
        path = Path(base or Path.home()) / "ytdl-data"
    elif is_windows():
        path = Path(os.environ.get("APPDATA") or Path.home()) / APP_DIRNAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DIRNAME
    else:
        path = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "ytdl"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    """Cache do yt-dlp. Em alguns Androids ``~/.cache`` não é gravável."""
    path = user_data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def staging_dir() -> Path:
    """Pasta temporária de download (usada no Android antes de copiar para
    o armazenamento compartilhado)."""
    path = user_data_dir() / "staging"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file() -> Path:
    return user_data_dir() / "settings.json"


def _windows_downloads_dir() -> Optional[Path]:
    """Pasta "Downloads" real do Windows (respeita redirecionamentos)."""
    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        # FOLDERID_Downloads = {374DE290-123F-4565-9164-39C4925E467B}
        folder_id = GUID(
            0x374DE290, 0x123F, 0x4565,
            (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B),
        )
        func = ctypes.windll.shell32.SHGetKnownFolderPath  # type: ignore[attr-defined]
        func.argtypes = [
            ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]
        out = ctypes.c_wchar_p()
        if func(ctypes.byref(folder_id), 0, None, ctypes.byref(out)) == 0:
            try:
                return Path(out.value)
            finally:
                ctypes.windll.ole32.CoTaskMemFree(out)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - qualquer falha cai no fallback
        pass
    return None


def _xdg_downloads_dir() -> Optional[Path]:
    """Lê ``XDG_DOWNLOAD_DIR`` de ~/.config/user-dirs.dirs (Linux)."""
    try:
        cfg = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "user-dirs.dirs"
        for line in cfg.read_text(encoding="utf-8").splitlines():
            if line.startswith("XDG_DOWNLOAD_DIR"):
                value = line.split("=", 1)[1].strip().strip('"')
                return Path(value.replace("$HOME", str(Path.home())))
    except Exception:  # noqa: BLE001
        pass
    return None


def default_download_dir() -> Path:
    """Pasta padrão de saída: ``<Downloads>/YTDL`` (desktop).

    No Android os arquivos são baixados para ``staging_dir()`` e depois
    copiados para ``Download/`` via MediaStore (ver ``platform_utils``).
    """
    if is_android():
        return staging_dir()
    base: Optional[Path] = None
    if is_windows():
        base = _windows_downloads_dir()
    elif not sys.platform == "darwin":
        base = _xdg_downloads_dir()
    base = base or (Path.home() / "Downloads")
    return base / "YTDL"
