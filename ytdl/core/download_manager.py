"""Fila de downloads: paralelismo configurável, cancelar, repetir, eventos.

Sem dependência de Kivy. Os *listeners* são chamados a partir das threads de
download; a UI é responsável por reenviar para a thread principal
(``Clock.schedule_once``). Isso mantém o núcleo independente do framework.
"""
from __future__ import annotations

import itertools
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, List, Optional

from ..logger import get_logger
from .errors import Cancelled, classify_exception
from .models import FormatOption, MediaItem, Progress
from .worker import CancelToken

log = get_logger("downloads")

# Estados de uma tarefa
QUEUED = "queued"
RUNNING = "running"
POSTPROCESSING = "postprocessing"
DONE = "done"
ERROR = "error"
CANCELLED = "cancelled"

ACTIVE_STATES = (QUEUED, RUNNING, POSTPROCESSING)
FINISHED_STATES = (DONE, ERROR, CANCELLED)

MAX_WORKERS = 4                 # teto de threads; o limite real vem das configurações
_MIN_EMIT_INTERVAL = 0.10       # no máximo ~10 atualizações/s por tarefa

Listener = Callable[[str, "DownloadTask"], None]


class DownloadTask:
    """Estado de um download. Atributos só são ESCRITOS pelo gerenciador."""

    _ids = itertools.count(1)

    def __init__(self, item: MediaItem, option: FormatOption) -> None:
        self.id = next(self._ids)
        self.item = item
        self.option = option
        self.state = QUEUED
        self.progress = Progress(stage="queued")
        self.filepath = ""
        self.location = ""          # texto amigável do destino final
        self.error_key = ""
        self.error_detail = ""
        self.token = CancelToken()
        self._last_emit = 0.0

    @property
    def fraction(self) -> Optional[float]:
        return self.progress.fraction

    @property
    def active(self) -> bool:
        return self.state in ACTIVE_STATES

    def __repr__(self) -> str:
        return f"<DownloadTask #{self.id} {self.state} {self.item.title[:30]!r} {self.option.key}>"


class DownloadManager:
    def __init__(
        self,
        service: Any,
        settings: Any,
        out_dir: Callable[[], str],
        publisher: Optional[Callable[[str], str]] = None,
    ) -> None:
        """
        :param service: objeto com ``download(url, option, out_dir, token, report)``.
        :param out_dir: função que devolve a pasta de saída atual.
        :param publisher: pós-processamento do arquivo pronto (Android: copia
            para ``Download/`` e devolve o local). Retorna texto do destino.
        """
        self._service = service
        self._settings = settings
        self._out_dir = out_dir
        self._publisher = publisher
        self._listeners: List[Listener] = []
        self._tasks: List[DownloadTask] = []
        self._queue: Deque[DownloadTask] = deque()
        self._cond = threading.Condition()
        self._running = 0
        self._shutdown = False
        self._threads: List[threading.Thread] = []

    # -- API pública -------------------------------------------------------- #
    @property
    def tasks(self) -> List[DownloadTask]:
        return list(self._tasks)

    def add_listener(self, callback: Listener) -> None:
        self._listeners.append(callback)

    def enqueue(self, item: MediaItem, option: FormatOption) -> DownloadTask:
        task = DownloadTask(item, option)
        with self._cond:
            self._tasks.append(task)
            self._queue.append(task)
            self._ensure_workers()
            self._cond.notify_all()
        log.info("Na fila: %r (%s)", item.title[:60], option.key)
        self._emit("added", task)
        return task

    def cancel(self, task: DownloadTask) -> None:
        with self._cond:
            if task.state == QUEUED:
                self._set_state(task, CANCELLED)
                try:
                    self._queue.remove(task)
                except ValueError:
                    pass
                log.info("Cancelada na fila: %r", task.item.title[:60])
                return
        if task.active:
            task.token.cancel()  # a thread de download aborta no próximo evento

    def retry(self, task: DownloadTask) -> None:
        """Reenfileira uma tarefa que falhou/foi cancelada (retoma ``.part``)."""
        if task.state not in (ERROR, CANCELLED):
            return
        task.token = CancelToken()
        task.error_key = task.error_detail = ""
        task.progress = Progress(stage="queued")
        with self._cond:
            self._queue.append(task)
            self._set_state(task, QUEUED)
            self._ensure_workers()
            self._cond.notify_all()

    def remove(self, task: DownloadTask) -> None:
        if task.active:
            self.cancel(task)
        with self._cond:
            if task in self._tasks:
                self._tasks.remove(task)
        self._emit("removed", task)

    def clear_finished(self) -> None:
        for task in [t for t in self._tasks if t.state in FINISHED_STATES]:
            self.remove(task)

    def active_count(self) -> int:
        return sum(1 for t in self._tasks if t.active)

    def overall_fraction(self) -> Optional[float]:
        """Progresso agregado das tarefas ativas (None = nada ou indeterminado)."""
        active = [t for t in self._tasks if t.active]
        if not active:
            return None
        values = [(t.fraction if t.fraction is not None else 0.0) for t in active]
        return sum(values) / len(values)

    def shutdown(self) -> None:
        """Cancela tudo e encerra as threads (chamado ao fechar o app)."""
        with self._cond:
            self._shutdown = True
            for task in self._tasks:
                task.token.cancel()
            self._cond.notify_all()

    # -- internos ----------------------------------------------------------- #
    def _limit(self) -> int:
        try:
            return max(1, min(MAX_WORKERS, int(self._settings.get("max_parallel"))))
        except (TypeError, ValueError):
            return 2

    def _ensure_workers(self) -> None:
        """Cria threads sob demanda (chamado com o lock adquirido)."""
        alive = [t for t in self._threads if t.is_alive()]
        self._threads = alive
        wanted = min(MAX_WORKERS, len(self._queue) + self._running)
        for _ in range(max(0, wanted - len(alive))):
            thread = threading.Thread(
                target=self._worker_loop, name=f"ytdl-dl-{len(self._threads) + 1}", daemon=True)
            self._threads.append(thread)
            thread.start()

    def _worker_loop(self) -> None:
        while True:
            with self._cond:
                while not self._shutdown and (not self._queue or self._running >= self._limit()):
                    self._cond.wait(timeout=1.0)
                    if self._shutdown:
                        return
                if self._shutdown:
                    return
                task = self._queue.popleft()
                if task.state != QUEUED:       # cancelada enquanto esperava
                    continue
                self._running += 1
                self._set_state(task, RUNNING)
            try:
                self._run(task)
            finally:
                with self._cond:
                    self._running -= 1
                    self._cond.notify_all()

    def _run(self, task: DownloadTask) -> None:
        log.info("Iniciando download #%d: %r", task.id, task.item.title[:60])

        def report(progress: Progress) -> None:
            task.progress = progress
            if progress.stage == "postprocess" and task.state != POSTPROCESSING:
                self._set_state(task, POSTPROCESSING)
                return
            now = time.monotonic()
            if now - task._last_emit >= _MIN_EMIT_INTERVAL or progress.fraction in (0.0, 1.0):
                task._last_emit = now
                self._emit("updated", task)

        try:
            result = self._service.download(
                task.item.url, task.option, self._out_dir(), task.token, report)
            task.filepath = result.filepath
            task.location = result.filepath
            if self._publisher:
                report(Progress(stage="publishing", fraction=1.0))
                task.location = self._publisher(result.filepath)
            task.progress = Progress(stage="done", fraction=1.0)
            self._set_state(task, DONE)
            log.info("Concluído #%d -> %s", task.id, task.location)
        except Cancelled:
            self._set_state(task, CANCELLED)
            log.info("Cancelado #%d", task.id)
        except Exception as exc:  # noqa: BLE001 - qualquer falha é reportada na tarefa
            err = classify_exception(exc)
            task.error_key, task.error_detail = err.key, err.detail
            log.error("Falha #%d [%s]: %s", task.id, err.key, err.detail or exc, exc_info=True)
            self._set_state(task, ERROR)

    def _set_state(self, task: DownloadTask, state: str) -> None:
        task.state = state
        self._emit("updated", task)

    def _emit(self, event: str, task: DownloadTask) -> None:
        for listener in list(self._listeners):
            try:
                listener(event, task)
            except Exception:  # noqa: BLE001 - listener nunca derruba a fila
                log.exception("Listener da fila falhou")
