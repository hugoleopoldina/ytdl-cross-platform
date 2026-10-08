"""Exceções do app e tradução de erros técnicos em mensagens para o usuário."""
from __future__ import annotations


class Cancelled(Exception):
    """Operação cancelada pelo usuário."""


class UserFacingError(Exception):
    """Erro com uma *chave* de tradução (``i18n``) e o detalhe técnico para o log."""

    def __init__(self, key: str, detail: str = "") -> None:
        super().__init__(key if not detail else f"{key}: {detail}")
        self.key = key
        self.detail = detail


# Cada regra: (trecho em minúsculas da mensagem, chave de tradução).
# A ORDEM importa: a primeira que casar vence.
_RULES = (
    # Idade ANTES de bot: as duas mensagens começam com "Sign in to confirm".
    ("confirm your age", "err_age"),
    ("age-restricted", "err_age"),
    ("not a bot", "err_bot_check"),
    ("private video", "err_private"),
    ("members-only", "err_private"),
    ("join this channel", "err_private"),
    ("not available in your country", "err_geo"),
    ("blocked it in your country", "err_geo"),
    ("video unavailable", "err_unavailable"),
    ("has been removed", "err_unavailable"),
    ("this video is not available", "err_unavailable"),
    ("http error 404", "err_unavailable"),
    ("http error 410", "err_unavailable"),
    ("http error 403", "err_forbidden"),
    ("is not a valid url", "err_invalid_url"),
    ("unsupported url", "err_invalid_url"),
    ("ffmpeg", "err_ffmpeg"),
    ("requested format is not available", "err_no_format"),
    ("no video formats found", "err_no_format"),
    ("only images are available", "err_no_format"),
    ("http error 429", "err_rate_limit"),
    ("too many requests", "err_rate_limit"),
    ("getaddrinfo failed", "err_network"),
    ("name or service not known", "err_network"),
    ("temporary failure in name resolution", "err_network"),
    ("network is unreachable", "err_network"),
    ("timed out", "err_network"),
    ("connection reset", "err_network"),
    ("unable to download webpage", "err_network"),
    ("urlopen error", "err_network"),
    ("certificate verify failed", "err_ssl"),
    ("permission denied", "err_permission"),
    ("no space left", "err_disk_full"),
)


def classify_exception(exc: BaseException) -> UserFacingError:
    """Converte qualquer exceção em :class:`UserFacingError`.

    A mensagem original é preservada em ``detail`` e vai para o log; ao
    usuário mostramos apenas o texto traduzido da chave.
    """
    if isinstance(exc, UserFacingError):
        return exc
    text = str(exc)
    lowered = text.lower()
    for needle, key in _RULES:
        if needle in lowered:
            return UserFacingError(key, text)
    return UserFacingError("err_unknown", text)
