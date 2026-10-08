"""Carregamento modal com progresso REAL.

No app original o carregamento era uma animação que durava um tempo FIXO,
independente do trabalho feito. Aqui a barra reflete o andamento verdadeiro:

* **indeterminada** (animada) enquanto o tamanho do trabalho é desconhecido
  (ex.: aguardando a resposta da rede);
* **determinada** (0-100 %) assim que o total é conhecido (ex.: 3 de 8 cartões
  montados, bytes baixados / bytes totais).

Troca de modo é automática: basta chamar :meth:`set_progress` com ``None`` ou
com uma fração.
"""
from __future__ import annotations

from typing import Callable, Optional

from kivy.animation import Animation
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.modalview import ModalView

from ...core.models import Progress
from ...i18n import tr


class LoadingOverlay(ModalView):
    title = StringProperty("")
    detail = StringProperty("")          # ex.: "3 / 8"
    percent_text = StringProperty("")    # ex.: "37%"
    indeterminate = BooleanProperty(True)
    cancellable = BooleanProperty(True)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._on_cancel: Optional[Callable[[], None]] = None

    # -- ciclo de vida ------------------------------------------------------ #
    def show(self, title: str, on_cancel: Optional[Callable[[], None]] = None) -> None:
        """Abre (ou reutiliza) o overlay em modo indeterminado."""
        self.title = title
        self.detail = ""
        self.percent_text = ""
        self.indeterminate = True
        self.cancellable = on_cancel is not None
        self._on_cancel = on_cancel
        self.ids.det_bar.value = 0
        self.open()                       # ModalView ignora se já estiver aberto
        self.ids.indet_bar.start()

    def close(self) -> None:
        self.ids.indet_bar.stop()
        Animation.cancel_all(self.ids.det_bar, "value")
        self._on_cancel = None
        self.dismiss()

    def cancel(self) -> None:
        callback, self._on_cancel = self._on_cancel, None
        if callback:
            callback()
        self.close()

    # -- atualização --------------------------------------------------------- #
    def set_progress(self, fraction: Optional[float], detail: str = "", title: str = "") -> None:
        """``fraction=None`` => animação indeterminada; ``0..1`` => barra real."""
        if title:
            self.title = title
        self.detail = detail
        if fraction is None:
            self.indeterminate = True
            self.percent_text = ""
            return
        fraction = max(0.0, min(1.0, fraction))
        if self.indeterminate:               # primeiro valor real: troca de barra
            self.indeterminate = False
            self.ids.det_bar.value = 0
        self.percent_text = "%d%%" % round(fraction * 100)
        Animation.cancel_all(self.ids.det_bar, "value")
        Animation(value=fraction * 100, duration=0.18, t="out_quad").start(self.ids.det_bar)

    def update(self, progress: Progress) -> None:
        """Atalho: aplica um :class:`Progress` vindo do núcleo."""
        detail = ""
        if progress.current is not None and progress.total:
            detail = f"{progress.current} / {progress.total}"
        self.set_progress(progress.fraction, detail)
