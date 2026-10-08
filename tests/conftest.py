import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Isola configurações/logs dos testes do perfil real do usuário.
_tmp = tempfile.mkdtemp(prefix="ytdl-tests-")
os.environ["XDG_DATA_HOME"] = _tmp
os.environ["APPDATA"] = _tmp
os.environ.setdefault("YTDL_LANG", "pt")
