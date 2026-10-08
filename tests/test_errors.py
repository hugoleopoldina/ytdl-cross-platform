import pytest

from ytdl.core.errors import UserFacingError, classify_exception
from ytdl.i18n import EN, PT


@pytest.mark.parametrize("message,key", [
    ("ERROR: [youtube] x: Sign in to confirm you’re not a bot", "err_bot_check"),
    ("Sign in to confirm your age", "err_age"),
    ("Private video. Sign in if you've been granted access", "err_private"),
    ("Video unavailable", "err_unavailable"),
    ("Unable to download webpage: HTTP Error 404: Not Found", "err_unavailable"),
    ("Unable to download webpage: HTTP Error 403: Forbidden", "err_forbidden"),
    ("<urlopen error [Errno -2] Name or service not known>", "err_network"),
    ("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed", "err_ssl"),
    ("ffmpeg not found", "err_ffmpeg"),
    ("Requested format is not available", "err_no_format"),
    ("HTTP Error 429: Too Many Requests", "err_rate_limit"),
    ("[Errno 28] No space left on device", "err_disk_full"),
    ("something nobody expected", "err_unknown"),
])
def test_classification(message, key):
    err = classify_exception(Exception(message))
    assert err.key == key
    assert message in err.detail


def test_user_facing_error_passthrough():
    err = UserFacingError("err_network", "x")
    assert classify_exception(err) is err


def test_every_error_key_has_translation():
    from ytdl.core import errors
    keys = {k for _needle, k in errors._RULES} | {"err_unknown"}
    assert keys <= set(PT) and keys <= set(EN)
