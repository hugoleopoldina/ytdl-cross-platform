"""Infra de concorrência: token de cancelamento e pool de threads de fundo."""
from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Optional

from ..logger import get_logger
from .errors import Cancelled, classify_exception, UserFacingError

log = get_logger("worker")

# Pool compartilhado para buscas/resoluções (downloads têm workers próprios).
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ytdl-bg")


class CancelToken:
    """Sinal de cancelamento cooperativo.

    Threads não podem ser mortas com segurança; em vez disso o código longo
    chama :meth:`raise_if_cancelled` em pontos seguros (ex.: a cada evento de
    progresso do yt-dlp) e a operação aborta com :class:`Cancelled`.
    """

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise Cancelled()


def run_background(
    func: Callable[[], Any],
    on_done: Callable[[Any], None],
    on_error: Callable[[UserFacingError], None],
    dispatch: Callable[[Callable[[], None]], None],
    token: Optional[CancelToken] = None,
) -> Future:
    """Executa ``func`` em thread de fundo e entrega o resultado via ``dispatch``.

    ``dispatch`` agenda a chamada na thread da UI (no app é ``Clock.schedule_once``).
    Se o ``token`` foi cancelado, NENHUM callback é chamado: a UI já seguiu em frente.
    """

    def job() -> None:
        try:
            result = func()
        except Cancelled:
            log.info("Operação cancelada")
            return
        except Exception as exc:  # noqa: BLE001 - toda falha vira mensagem ao usuário
            err = classify_exception(exc)
            log.error("Operação falhou [%s]: %s", err.key, err.detail or exc, exc_info=True)
            if token is None or not token.cancelled:
                dispatch(lambda: on_error(err))
            return
        if token is not None and token.cancelled:
            log.info("Resultado descartado (operação cancelada)")
            return
        dispatch(lambda: on_done(result))

    return _pool.submit(job)
