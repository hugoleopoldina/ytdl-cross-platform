"""Serviço FALSO para o modo ``--demo`` (``python main.py --demo``).

Implementa a mesma interface de :class:`~ytdl.core.ytdlp_service.YtdlpService`
mas sem rede: gera resultados fictícios, miniaturas locais e simula progresso
de download. Serve para:

* desenvolver e ajustar a interface sem depender do YouTube;
* testes automáticos de interface (``scripts/smoke_test.py``);
* demonstrar o app em lugares sem internet.
"""
from __future__ import annotations

import os
import random
import tempfile
import time
from typing import Any, Dict, List

from ..logger import get_logger
from .models import (KIND_LIVE, KIND_PLAYLIST, KIND_SHORT, KIND_VIDEO, FormatOption,
                     MediaItem, Progress, SearchPage)
from .worker import CancelToken
from .ytdlp_service import DownloadResult, generic_format_options

log = get_logger("fake")

# (título, canal, duração em s, visualizações, tipo)
_CATALOG = [
    ("Lo-fi hip hop beats para estudar e relaxar 📚", "Chill Station", 3725, 1_820_000, KIND_VIDEO),
    ("Como fazer pão caseiro em 5 passos simples 🍞", "Cozinha da Vovó", 842, 340_500, KIND_VIDEO),
    ("日本の夜景 – Tokyo Night Walk 4K", "Walk Around", 2710, 9_400_000, KIND_VIDEO),
    ("Gol incrível aos 90 minutos! ⚽🔥", "Futebol Total", 58, 12_300_000, KIND_SHORT),
    ("Rádio 24h ao vivo – Música instrumental", "Rádio Zen", None, 3_100, KIND_LIVE),
    ("Tutorial de Python para iniciantes (curso completo)", "Código Limpo", 14_300, 2_750_000, KIND_VIDEO),
    ("Os melhores momentos da Copa 2022", "Esporte News", 1_190, 780_000, KIND_VIDEO),
    ("Paisagens da Patagônia em 8K HDR", "Natureza Viva", 1_805, 45_200, KIND_VIDEO),
    ("Dica rápida de Excel que ninguém te contou", "Planilhas Pro", 47, 980_000, KIND_SHORT),
    ("Entrevista completa: o futuro da inteligência artificial", "Tech Podcast", 5_420, 410_000, KIND_VIDEO),
    ("Documentário: A vida no fundo do oceano", "Mundo Selvagem", 3_300, 6_700_000, KIND_VIDEO),
    ("Treino de 20 minutos em casa, sem equipamento", "Fit Brasil", 1_260, 150_800, KIND_VIDEO),
    ("Playlist: Clássicos do Rock Nacional", "Rock BR", None, 920_000, KIND_PLAYLIST),
    ("Review: o smartphone mais vendido do ano", "Giro Tech", 960, 1_230_000, KIND_VIDEO),
    ("Receita de bolo de cenoura com cobertura", "Cozinha da Vovó", 615, 2_100_000, KIND_VIDEO),
    ("Aula de violão: primeiros acordes", "Violão Fácil", 1_540, 88_000, KIND_VIDEO),
]


def _make_thumbnail(seed: int, directory: str) -> str:
    """Gera uma miniatura em gradiente (PNG local) para não precisar de rede."""
    from PIL import Image, ImageDraw

    path = os.path.join(directory, f"thumb_{seed}.png")
    if os.path.exists(path):
        return path
    rng = random.Random(seed)
    top = tuple(rng.randint(30, 200) for _ in range(3))
    bottom = tuple(rng.randint(30, 200) for _ in range(3))
    width, height = 480, 270
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / height
        draw.line([(0, y), (width, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3)))
    # "play" translúcido no centro
    cx, cy = width // 2, height // 2
    draw.polygon([(cx - 26, cy - 34), (cx - 26, cy + 34), (cx + 36, cy)], fill=(255, 255, 255))
    image.save(path)
    return path


class FakeService:
    """Mesma interface do ``YtdlpService``, sem rede."""

    def __init__(self, settings: Any, simulate_seconds: float = 3.0) -> None:
        self._settings = settings
        self._simulate = simulate_seconds
        self._thumb_dir = tempfile.mkdtemp(prefix="ytdl-demo-")

    def capabilities(self) -> Dict[str, bool]:
        return {"ffmpeg": True, "js_runtime": True}

    def _item(self, index: int) -> MediaItem:
        title, channel, duration, views, kind = _CATALOG[index % len(_CATALOG)]
        return MediaItem(
            id=f"demo{index:04d}", url=f"https://demo.invalid/watch?v=demo{index:04d}",
            title=title, kind=kind, duration=duration, channel=channel, views=views,
            thumbnail=_make_thumbnail(index, self._thumb_dir),
            count=12 if kind == KIND_PLAYLIST else None)

    def search(self, query: str, limit: int, offset: int, token: CancelToken,
               report=lambda _p: None) -> SearchPage:
        report(Progress(stage="search", message=query))
        time.sleep(1.2)  # latência de rede simulada (barra indeterminada)
        token.raise_if_cancelled()
        total = 40
        items = [self._item(i) for i in range(offset, min(offset + limit, total))]
        return SearchPage(items=items, has_more=offset + limit < total)

    def resolve(self, url: str, token: CancelToken, report=lambda _p: None) -> MediaItem:
        report(Progress(stage="resolve", message=url))
        time.sleep(0.8)
        token.raise_if_cancelled()
        index = int(url.rsplit("demo", 1)[-1]) if "demo" in url else 0
        item = self._item(index)
        if item.kind == KIND_PLAYLIST:
            item.entries = [self._item(i + 100) for i in range(12)]
            for n, entry in enumerate(item.entries):
                entry.kind = KIND_VIDEO
                entry.duration = entry.duration or 200 + n * 13
            item.formats = generic_format_options()
        else:
            item.formats = [
                FormatOption("audio_m4a", "audio", "M4A", "m4a", "", size=4_200_000, note="sem conversão"),
                FormatOption("video_prog", "video", "MP4 360p", "mp4", "", size=18_400_000, note="sem conversão"),
                FormatOption("audio_mp3", "audio", "MP3", "mp3", "", needs_ffmpeg=True, size=7_900_000),
                FormatOption("video_1080", "video", "MP4 1080p", "mp4", "", needs_ffmpeg=True, size=96_000_000),
                FormatOption("video_720", "video", "MP4 720p", "mp4", "", needs_ffmpeg=True, size=52_000_000),
            ]
        return item

    def download(self, url: str, option: FormatOption, out_dir: str, token: CancelToken,
                 report=lambda _p: None) -> DownloadResult:
        os.makedirs(out_dir, exist_ok=True)
        report(Progress(stage="connecting"))
        time.sleep(0.6)
        total = option.size or 20_000_000
        steps = 40
        for step in range(1, steps + 1):
            token.raise_if_cancelled()
            time.sleep(self._simulate / steps)
            done = int(total * step / steps)
            report(Progress(stage="download", fraction=step / steps, downloaded=done,
                            total_bytes=total, speed=total / max(self._simulate, 0.1),
                            eta=int(self._simulate * (1 - step / steps))))
        if option.needs_ffmpeg:
            report(Progress(stage="postprocess", message="Merger"))
            time.sleep(0.8)
        path = os.path.join(out_dir, f"demo-{abs(hash(url)) % 10_000}.{option.ext}")
        with open(path, "wb") as handle:
            handle.write(b"demo")
        return DownloadResult(path, {"id": url})
