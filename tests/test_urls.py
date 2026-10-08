import pytest

from ytdl.core.urls import (QUERY_EMPTY, QUERY_PLAYLIST, QUERY_SEARCH, QUERY_VIDEO,
                            classify_query)

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize("text,kind", [
    ("", QUERY_EMPTY),
    ("   ", QUERY_EMPTY),
    ("phonk 2023", QUERY_SEARCH),
    (f"https://youtu.be/{VID}?t=3", QUERY_VIDEO),
    (f"https://www.youtube.com/watch?v={VID}", QUERY_VIDEO),
    (f"https://m.youtube.com/watch?v={VID}", QUERY_VIDEO),
    (f"https://music.youtube.com/watch?v={VID}", QUERY_VIDEO),
    (f"https://www.youtube.com/shorts/{VID}", QUERY_VIDEO),
    (f"www.youtube.com/watch?v={VID}", QUERY_VIDEO),
    ("https://www.youtube.com/playlist?list=PLabc123", QUERY_PLAYLIST),
    (f"https://www.youtube.com/watch?v={VID}&list=PLabc123", QUERY_PLAYLIST),
    # Mix/Rádio automáticos do YouTube são infinitos: tratados como vídeo
    (f"https://www.youtube.com/watch?v={VID}&list=RD{VID}", QUERY_VIDEO),
    ("https://vimeo.com/123456", QUERY_VIDEO),
    ("https://www.youtube.com/@canal", QUERY_SEARCH),
])
def test_classify(text, kind):
    assert classify_query(text).kind == kind


def test_video_url_is_normalized():
    q = classify_query(f"https://youtu.be/{VID}?t=3&feature=share")
    assert q.text == f"https://www.youtube.com/watch?v={VID}"
    assert q.video_id == VID


def test_playlist_inside_watch_url_becomes_playlist_page():
    q = classify_query(f"https://www.youtube.com/watch?v={VID}&list=PLxyz&index=2")
    assert q.text == "https://www.youtube.com/playlist?list=PLxyz"
