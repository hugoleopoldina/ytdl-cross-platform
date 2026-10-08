"""Conversão de dicionários do yt-dlp (formato real) em modelos do app."""
from ytdl.core.models import KIND_LIVE, KIND_PLAYLIST, KIND_SHORT, KIND_VIDEO
from ytdl.core.ytdlp_service import (build_format_options, generic_format_options,
                                     pick_thumbnail, to_media_item)

# Formato de um resultado "flat" de ytsearch (campos reais do yt-dlp).
FLAT = {
    "_type": "url", "ie_key": "Youtube", "id": "dQw4w9WgXcQ", "title": "Música 🎵",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "duration": 212.0,
    "channel": "Canal", "view_count": 1_500_000, "live_status": None,
    "thumbnails": [
        {"url": "https://i.ytimg.com/vi/x/hqdefault.jpg?sqp=a", "width": 168, "height": 94},
        {"url": "https://i.ytimg.com/vi/x/hq720.jpg?sqp=b", "width": 480, "height": 270},
        {"url": "https://i.ytimg.com/vi/x/maxres.jpg?sqp=c", "width": 1280, "height": 720},
    ],
}


def test_flat_video():
    item = to_media_item(FLAT)
    assert (item.kind, item.duration, item.views, item.channel) == (KIND_VIDEO, 212, 1_500_000, "Canal")
    assert item.url.endswith("dQw4w9WgXcQ")
    assert item.display_title == "Música"           # emoji removido só na exibição
    assert item.title == "Música 🎵"                 # original preservado


def test_thumbnail_prefers_mid_size_jpeg():
    assert "hq720" in pick_thumbnail(FLAT)
    assert pick_thumbnail({"id": "abcdefghijk", "ie_key": "Youtube"}).endswith("/abcdefghijk/hqdefault.jpg")
    assert pick_thumbnail({}) == ""


def test_kinds():
    assert to_media_item(dict(FLAT, url="https://www.youtube.com/shorts/dQw4w9WgXcQ")).kind == KIND_SHORT
    assert to_media_item(dict(FLAT, live_status="is_live", duration=None)).kind == KIND_LIVE
    assert to_media_item(dict(FLAT, is_live=True)).kind == KIND_LIVE
    pl = to_media_item({"_type": "playlist", "id": "PL1", "title": "Lista", "playlist_count": 12,
                        "webpage_url": "https://www.youtube.com/playlist?list=PL1"})
    assert pl.kind == KIND_PLAYLIST and pl.count == 12


def test_missing_fields_do_not_crash():
    item = to_media_item({"id": "x"})
    assert item.title and item.duration is None and item.views is None


def _fmt(**kw):
    base = {"vcodec": "none", "acodec": "none"}
    base.update(kw)
    return base


FULL = {
    "duration": 200,
    "formats": [
        _fmt(format_id="140", ext="m4a", acodec="mp4a.40.2", abr=128, filesize=3_000_000),
        _fmt(format_id="251", ext="webm", acodec="opus", abr=160, filesize=3_400_000),
        _fmt(format_id="18", ext="mp4", vcodec="avc1", acodec="mp4a", height=360, filesize=12_000_000),
        _fmt(format_id="137", ext="mp4", vcodec="avc1", height=1080, filesize=60_000_000),
        _fmt(format_id="136", ext="mp4", vcodec="avc1", height=720, filesize_approx=30_000_000),
        _fmt(format_id="160", ext="mp4", vcodec="avc1", height=144, filesize=1_000_000),
    ],
}


def test_format_options_from_real_shaped_info():
    options = {o.key: o for o in build_format_options(FULL)}
    assert options["audio_m4a"].size == 3_000_000 and not options["audio_m4a"].needs_ffmpeg
    assert options["video_prog"].label == "MP4 360p" and not options["video_prog"].needs_ffmpeg
    assert options["audio_mp3"].needs_ffmpeg and options["audio_mp3"].audio_codec == "mp3"
    assert options["video_1080"].size == 63_000_000          # vídeo + melhor m4a
    assert options["video_720"].needs_ffmpeg and options["video_720"].merge_to == "mp4"
    assert "video_144" not in options                        # abaixo de 360p é omitido
    # Tudo que dispensa ffmpeg vem antes do que precisa dele (ordem de exibição)
    order = [o.key for o in build_format_options(FULL)]
    assert order.index("video_prog") < order.index("video_1080")


def test_format_options_without_progressive_and_empty_info():
    only_split = {"formats": [f for f in FULL["formats"] if f["format_id"] != "18"]}
    assert "video_prog" not in {o.key for o in build_format_options(only_split)}
    assert {o.key for o in build_format_options({})} == {"audio_m4a", "audio_mp3"}


def test_generic_options_cover_all_needs():
    keys = [o.key for o in generic_format_options()]
    assert keys[:1] == ["audio_m4a"] and "video_prog" in keys and "audio_mp3" in keys
