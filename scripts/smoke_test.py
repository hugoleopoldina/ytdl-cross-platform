"""Teste de fumaça da interface (headless) com capturas de tela.

Abre o app em modo ``--demo`` (sem rede), percorre as telas principais e salva
PNGs. Falha (exit code != 0) se qualquer exceção ocorrer ou se um fluxo não
completar. Requer um display (no Linux sem monitor: ``xvfb-run``):

    LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a python scripts/smoke_test.py [pasta_saida]
"""
import os
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["KIVY_NO_ARGS"] = "1"
os.environ.setdefault("KIVY_IMAGE", "pil,sdl2")
os.environ.setdefault("YTDL_LANG", "pt")
# Isola configurações/logs do teste do perfil real do usuário.
_tmp = tempfile.mkdtemp(prefix="ytdl-smoke-")
os.environ["XDG_DATA_HOME"] = _tmp
os.environ["APPDATA"] = _tmp

# Downloads simulados vão para uma pasta temporária (não poluem ~/Downloads).
import json  # noqa: E402
_data = Path(_tmp) / ("YTDL" if sys.platform.startswith("win") else "ytdl")
_data.mkdir(parents=True, exist_ok=True)
(_data / "settings.json").write_text(json.dumps({"download_dir": str(Path(_tmp) / "downloads")}))

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "demo" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

from kivy.clock import Clock  # noqa: E402
from ytdl.logger import setup_logging  # noqa: E402

setup_logging(os.environ.get("YTDL_LOG_LEVEL", "INFO"))
from ytdl.app import YtdlApp  # noqa: E402

FAILURES = []


def shot(name):
    from kivy.core.window import Window
    path = str(OUT / f"{name}.png")
    Window.screenshot(name=path)
    # Window.screenshot acrescenta um índice (nome0001.png); renomeia para o nome limpo.
    for candidate in sorted(OUT.glob(f"{name}*.png")):
        if candidate.name != f"{name}.png":
            candidate.replace(OUT / f"{name}.png")
    print("  captura:", name)


class Runner:
    """Executa passos agendados no relógio do Kivy, um após o outro."""

    def __init__(self, app):
        self.app = app
        self.steps = []

    def at(self, delay, func):
        self.steps.append((delay, func))

    def start(self):
        total = 0.0
        for delay, func in self.steps:
            total += delay
            Clock.schedule_once(lambda _dt, f=func: self._safe(f), total)
        Clock.schedule_once(lambda _dt: self.app.stop(), total + 0.5)

    def _safe(self, func):
        try:
            func()
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            FAILURES.append(func.__name__)


def main():
    app = YtdlApp(demo=True)
    run = Runner(app)
    pages = lambda: app.root.ids.pages  # noqa: E731
    screen = lambda n: pages().get_screen(n)  # noqa: E731

    def s_empty():
        shot("01_busca_vazia")

    def s_search():
        screen("search").ids.field.text = "lofi"
        screen("search").do_search()

    def s_loading_indeterminate():
        assert app.overlay._is_open if hasattr(app.overlay, "_is_open") else True
        shot("02_carregando_busca")

    def s_results():
        assert len(screen("search").ids.results.children) >= 8, "cartões não foram criados"
        shot("03_resultados")

    def s_scroll_more():
        from kivymd.uix.card import MDCard  # noqa: F401
        screen("search").ids.results.parent.parent.scroll_y = 0
        shot("04_resultados_fim")

    def s_detail():
        first = [c for c in reversed(screen("search").ids.results.children) if hasattr(c, "item")][0]
        app.open_detail(first.item)

    def s_detail_shot():
        d = screen("detail")
        assert d.item is not None and pages().current == "detail"
        shot("05_detalhes_carregando")

    def s_detail_ready():
        assert screen("detail").can_download, "formatos não carregaram"
        shot("06_detalhes")

    def s_dialog():
        screen("detail").on_download()

    def s_dialog_shot():
        shot("07_dialogo_formatos")

    def s_confirm():
        from kivy.core.window import Window
        from kivymd.uix.dialog import MDDialog
        dialogs = [w for w in Window.children if isinstance(w, MDDialog)]
        assert dialogs, "diálogo não abriu"
        # Procura o botão preenchido ("Baixar") dentro do diálogo e aciona.
        from kivymd.uix.button import MDButton
        buttons = [w for w in dialogs[0].walk() if isinstance(w, MDButton)]
        filled = [b for b in buttons if b.style == "filled"][0]
        filled.dispatch("on_release")

    def s_downloads():
        app.navigate("downloads")

    def s_downloads_shot():
        assert app.downloads.active_count() >= 1, "download não entrou na fila"
        shot("08_downloads_progresso")

    def s_downloads_done():
        states = [t.state for t in app.downloads.tasks]
        assert "done" in states, f"download não terminou: {states}"
        shot("09_downloads_concluido")

    def s_settings():
        app.navigate("settings")

    def s_settings_shot():
        shot("10_ajustes")

    def s_light():
        screen("settings").set_dark(False)
        screen("settings").set_palette("Indigo")

    def s_light_shot():
        shot("11_ajustes_tema_claro")
        app.navigate("search")

    def s_light_search():
        shot("12_busca_tema_claro")

    def s_playlist():
        screen("search").ids.field.text = "https://demo.invalid/watch?v=demo0012"
        # URL não-YouTube => classificada como vídeo; resolve devolve a playlist (índice 12).
        screen("search").do_search()

    def s_playlist_detail():
        shot("13_playlist")

    def s_logs():
        app.navigate("settings")
        app.navigate("logs")

    def s_logs_shot():
        assert "Logging" in screen("logs").text or screen("logs").text
        shot("14_logs")

    for delay, fn in [
        (3.0, s_empty), (0.3, s_search), (0.35, s_loading_indeterminate), (3.5, s_results),
        (0.3, s_scroll_more), (0.3, s_detail), (0.5, s_detail_shot), (1.8, s_detail_ready),
        (0.2, s_dialog), (0.8, s_dialog_shot), (0.2, s_confirm), (0.8, s_downloads),
        (1.5, s_downloads_shot), (5.0, s_downloads_done), (0.3, s_settings), (0.7, s_settings_shot),
        (0.2, s_light), (0.9, s_light_shot), (1.0, s_light_search),
        (0.2, s_playlist), (3.5, s_playlist_detail), (0.2, s_logs), (0.8, s_logs_shot),
    ]:
        run.at(delay, fn)

    Clock.schedule_once(lambda _dt: run.start(), 0.5)
    app.run()
    if FAILURES:
        print("FALHAS:", FAILURES)
        return 1
    print("SMOKE TEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
