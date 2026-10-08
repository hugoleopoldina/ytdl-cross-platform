import json
import threading
import time

from ytdl.core import download_manager as dm
from ytdl.core.errors import Cancelled, UserFacingError
from ytdl.core.models import FormatOption, MediaItem, Progress
from ytdl.core.ytdlp_service import DownloadResult, _ProgressBridge
from ytdl.core.worker import CancelToken, run_background
from ytdl.settings import DEFAULTS, Settings

OPT = FormatOption("audio_m4a", "audio", "M4A", "m4a", "bestaudio")


def item(n=1):
    return MediaItem(id=str(n), url=f"https://x/{n}", title=f"vídeo {n}")


class StubService:
    def __init__(self, behaviour="ok", delay=0.0):
        self.behaviour, self.delay = behaviour, delay
        self.calls = []
        self.max_concurrent = 0
        self._active = 0
        self._lock = threading.Lock()

    def download(self, url, option, out_dir, token, report):
        with self._lock:
            self._active += 1
            self.max_concurrent = max(self.max_concurrent, self._active)
        try:
            self.calls.append(url)
            for step in range(5):
                token.raise_if_cancelled()
                time.sleep(self.delay)
                report(Progress(stage="download", fraction=(step + 1) / 5))
            if self.behaviour == "error":
                raise UserFacingError("err_network", "boom")
            return DownloadResult(f"{out_dir}/{url[-1]}.m4a", {})
        finally:
            with self._lock:
                self._active -= 1


def wait_for(cond, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def make(service, parallel=2, publisher=None):
    settings = Settings("/dev/null/never")  # arquivo inválido: usa padrões em memória
    settings.set("max_parallel", parallel, save=False)
    return dm.DownloadManager(service, settings, out_dir=lambda: "/tmp/out", publisher=publisher)


def test_successful_download_and_events():
    manager = make(StubService())
    events = []
    manager.add_listener(lambda e, t: events.append((e, t.state)))
    task = manager.enqueue(item(), OPT)
    assert wait_for(lambda: task.state == dm.DONE)
    assert task.filepath.endswith("1.m4a") and task.fraction == 1.0
    assert events[0] == ("added", dm.QUEUED)
    assert ("updated", dm.RUNNING) in events and ("updated", dm.DONE) in events
    manager.shutdown()


def test_parallel_limit_is_respected():
    service = StubService(delay=0.03)
    manager = make(service, parallel=2)
    tasks = [manager.enqueue(item(n), OPT) for n in range(1, 6)]
    assert wait_for(lambda: all(t.state == dm.DONE for t in tasks), 10)
    assert service.max_concurrent == 2
    manager.shutdown()


def test_error_is_classified_and_retry_works():
    service = StubService("error")
    manager = make(service)
    task = manager.enqueue(item(), OPT)
    assert wait_for(lambda: task.state == dm.ERROR)
    assert task.error_key == "err_network"
    service.behaviour = "ok"
    manager.retry(task)
    assert wait_for(lambda: task.state == dm.DONE) and task.error_key == ""
    manager.shutdown()


def test_cancel_running_and_queued():
    service = StubService(delay=0.1)
    manager = make(service, parallel=1)
    first, second = manager.enqueue(item(1), OPT), manager.enqueue(item(2), OPT)
    assert wait_for(lambda: first.state == dm.RUNNING)
    manager.cancel(second)                      # ainda na fila
    assert second.state == dm.CANCELLED
    manager.cancel(first)                       # em execução
    assert wait_for(lambda: first.state == dm.CANCELLED)
    assert service.calls == ["https://x/1"]     # a segunda nunca começou
    manager.shutdown()


def test_publisher_result_becomes_location_and_clear_finished():
    manager = make(StubService(), publisher=lambda path: "Download/YTDL/" + path.split("/")[-1])
    task = manager.enqueue(item(), OPT)
    assert wait_for(lambda: task.state == dm.DONE)
    assert task.location == "Download/YTDL/1.m4a"
    manager.clear_finished()
    assert manager.tasks == []
    manager.shutdown()


def test_overall_fraction():
    manager = make(StubService())
    assert manager.overall_fraction() is None
    manager.shutdown()


# ---- ponte de progresso: fração real e ponderada por bytes ----------------- #
def test_progress_bridge_weights_parts_by_size_and_never_goes_back():
    seen = []
    bridge = _ProgressBridge(CancelToken(), seen.append)
    info = {"requested_formats": [{"format_id": "137", "filesize": 900}, {"format_id": "140", "filesize": 100}]}
    video = {"format_id": "137", "requested_formats": info["requested_formats"]}
    audio = {"format_id": "140", "requested_formats": info["requested_formats"]}
    for done in (0, 450, 900):
        bridge.download_hook({"status": "downloading", "downloaded_bytes": done, "total_bytes": 900, "info_dict": video})
    bridge.download_hook({"status": "finished", "total_bytes": 900, "info_dict": video})
    bridge.download_hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100, "info_dict": audio})
    fractions = [p.fraction for p in seen if p.fraction is not None]
    assert fractions == sorted(fractions)                      # monotônica
    assert abs(fractions[2] - 0.9) < 1e-9                      # vídeo = 90% do total
    assert abs(fractions[-1] - 0.95) < 1e-9                    # + metade do áudio


def test_progress_bridge_cancel_raises():
    token = CancelToken()
    bridge = _ProgressBridge(token, lambda p: None)
    token.cancel()
    try:
        bridge.download_hook({"status": "downloading", "info_dict": {}})
        assert False, "deveria cancelar"
    except Cancelled:
        pass


# ---- worker ------------------------------------------------------------------ #
def test_run_background_dispatch_and_cancel_discards_result():
    results, dispatch = [], lambda fn: fn()
    done = threading.Event()
    run_background(lambda: 42, lambda r: (results.append(r), done.set()), lambda e: None, dispatch)
    assert done.wait(2) and results == [42]

    token = CancelToken()
    token.cancel()
    called = []
    future = run_background(lambda: 1, called.append, called.append, dispatch, token)
    future.result(2)
    assert called == []


def test_run_background_error_is_classified():
    got = []
    done = threading.Event()
    run_background(lambda: (_ for _ in ()).throw(Exception("HTTP Error 429")),
                   lambda r: None, lambda e: (got.append(e.key), done.set()), lambda fn: fn())
    assert done.wait(2) and got == ["err_rate_limit"]


# ---- settings ------------------------------------------------------------------ #
def test_settings_persist_validate_and_notify(tmp_path):
    path = tmp_path / "s.json"
    s = Settings(path)
    changes = []
    s.add_listener(lambda k, v: changes.append((k, v)))
    s.set("theme_style", "Light")
    s.set("theme_style", "Light")            # sem mudança: sem evento
    assert changes == [("theme_style", "Light")]
    assert Settings(path).get("theme_style") == "Light"
    try:
        s.set("nao_existe", 1)
        assert False
    except KeyError:
        pass


def test_settings_ignore_corrupt_or_wrongly_typed_values(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"max_parallel": "muitos", "theme_style": "Light", "lixo": 1}))
    s = Settings(path)
    assert s.get("max_parallel") == DEFAULTS["max_parallel"]     # tipo errado: ignorado
    assert s.get("theme_style") == "Light"
    path.write_text("{ isto não é json")
    assert Settings(path).get("theme_style") == DEFAULTS["theme_style"]
