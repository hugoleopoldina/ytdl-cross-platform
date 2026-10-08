"""Código dependente de plataforma (Android x desktop) em um único lugar.

Regra de ouro: NENHUM outro módulo faz ``from android import ...`` ou
``from jnius import ...``. Isso evita os erros do projeto original (por
exemplo, ``from android import autoclass``, que não existe) e permite rodar o
app no desktop sem esses pacotes instalados.
"""
from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from typing import Callable, Optional

from . import paths
from .logger import get_logger

log = get_logger("platform")

IS_ANDROID = paths.is_android()


# --------------------------------------------------------------------------- #
# SSL
# --------------------------------------------------------------------------- #
def setup_ssl() -> None:
    """Aponta o Python para os certificados do ``certifi``.

    O Python do Android NÃO tem repositório de certificados do sistema, e o
    app original falhava com ``CERTIFICATE_VERIFY_FAILED``. A variável
    ``SSL_CERT_FILE`` é respeitada por ``ssl.create_default_context`` (urllib,
    carregador de imagens do Kivy). O yt-dlp usa ``certifi`` por conta própria.
    """
    try:
        import certifi
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
        log.debug("SSL_CERT_FILE=%s", os.environ["SSL_CERT_FILE"])
    except ImportError:
        log.warning("certifi não instalado: conexões HTTPS podem falhar no Android")


# --------------------------------------------------------------------------- #
# Android: permissões e armazenamento compartilhado
# --------------------------------------------------------------------------- #
def request_storage_permissions() -> None:
    """Pede permissão de escrita SOMENTE no Android 9 (API 28) ou anterior.

    A partir do Android 10 a gravação em ``Download/`` é feita via MediaStore
    (``androidstorage4kivy``) e não exige permissão.
    """
    if not IS_ANDROID:
        return
    try:
        from android.permissions import Permission, request_permissions  # type: ignore
        from jnius import autoclass  # type: ignore

        sdk = autoclass("android.os.Build$VERSION").SDK_INT
        log.info("Android SDK_INT=%s", sdk)
        if sdk <= 28:
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE])
    except Exception:  # noqa: BLE001
        log.exception("Falha ao solicitar permissões de armazenamento")


def publish_download(path: str) -> str:
    """Torna o arquivo visível ao usuário.

    * **Android:** copia de ``staging`` (privado) para ``Download/<app>/`` via
      MediaStore e apaga a cópia privada. Retorna ``"Download/<app>/arquivo"``.
    * **Desktop:** o arquivo já está na pasta final; retorna o próprio caminho.
    """
    if not IS_ANDROID:
        return path
    from androidstorage4kivy import SharedStorage  # type: ignore
    from jnius import autoclass  # type: ignore

    from .core.errors import UserFacingError

    environment = autoclass("android.os.Environment")
    log.info("Copiando para armazenamento compartilhado: %s", path)
    # DIRECTORY_DOWNLOADS é aceito pela biblioteca para qualquer tipo de arquivo
    # (Android 10+: MediaStore.Downloads) e cria Download/<título do app>/.
    shared = SharedStorage().copy_to_shared(path, collection=environment.DIRECTORY_DOWNLOADS)
    if shared is None:
        # NUNCA apague a cópia privada se a cópia falhou: seria perda do download.
        raise UserFacingError("err_permission", f"copy_to_shared falhou para {path}")
    try:
        os.remove(path)
    except OSError:
        log.warning("Não foi possível apagar a cópia privada %s", path)
    return "Download/YTDL/" + os.path.basename(path)


# --------------------------------------------------------------------------- #
# Desktop: abrir pasta / link
# --------------------------------------------------------------------------- #
def open_folder(path: str) -> bool:
    """Abre ``path`` (ou a pasta que o contém) no gerenciador de arquivos."""
    if IS_ANDROID:
        return False
    target = path if os.path.isdir(path) else os.path.dirname(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(target)  # type: ignore[attr-defined]  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return True
    except Exception:  # noqa: BLE001
        log.exception("Não foi possível abrir a pasta %s", target)
        return False


def open_url(url: str) -> None:
    """Abre um link no navegador (Android: via Intent do pyjnius)."""
    if IS_ANDROID:
        try:
            from jnius import autoclass  # type: ignore

            intent = autoclass("android.content.Intent")
            uri = autoclass("android.net.Uri")
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            view = intent(intent.ACTION_VIEW, uri.parse(url))
            activity.startActivity(view)
            return
        except Exception:  # noqa: BLE001
            log.exception("Falha ao abrir URL via Intent")
    webbrowser.open(url)
