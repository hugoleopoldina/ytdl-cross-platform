from ytdl.core.formatting import (clean_display_text, format_bytes, format_count,
                                  format_duration, format_eta, format_speed, sanitize_filename)


def test_duration():
    assert format_duration(None) == ""
    assert format_duration(0) == "0:00"
    assert format_duration(65) == "1:05"
    assert format_duration(3725) == "1:02:05"
    assert format_duration(59.9) == "0:59"


def test_count():
    assert format_count(None) == ""
    assert format_count(999) == "999"
    assert format_count(1234) == "1,2 mil"
    assert format_count(1_000) == "1 mil"
    assert format_count(2_500_000) == "2,5 mi"
    assert format_count(3_000_000_000) == "3 bi"


def test_bytes_speed_eta():
    assert format_bytes(None) == "?"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1536) == "1,5 KB"
    assert format_bytes(5 * 1024 ** 2) == "5,0 MB"
    assert format_speed(None) == "" and format_speed(2048) == "2,0 KB/s"
    assert format_eta(None) == "" and format_eta(75) == "1:15"


def test_sanitize_filename():
    assert sanitize_filename('a/b\\c:d*e?f"g<h>i|j') == "a_b_c_d_e_f_g_h_i_j"
    assert sanitize_filename("") == "download"
    assert len(sanitize_filename("x" * 500)) == 150


def test_clean_display_text_removes_emoji_keeps_text():
    assert clean_display_text("Lo-fi 📚 beats 🔥🔥") == "Lo-fi beats"
    assert clean_display_text("café ★ 日本語") == "café ★ 日本語"
    assert clean_display_text("👨‍👩‍👧 família") == "família"
    assert clean_display_text("") == ""
