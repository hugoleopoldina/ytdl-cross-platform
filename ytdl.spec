# -*- mode: python ; coding: utf-8 -*-
"""Receita do PyInstaller para Windows e Linux (um único arquivo para os dois).

NÃO é preciso copiar a pasta do projeto: o PyInstaller lê direto de ``ytdl/``,
e o código encontra assets/.kv através de ``ytdl/paths.py`` (usa sys._MEIPASS).

Uso recomendado (veja o README):   python scripts/build_desktop.py [--onefile]

Variáveis de ambiente lidas aqui (o script de build as define):
    YTDL_ONEFILE=1   gera UM executável (inicia mais devagar: extrai em temp)
    YTDL_CONSOLE=1   mantém a janela de console (útil para ver logs no Windows)
"""
import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821  (SPECPATH é injetado pelo PyInstaller)
sys.path.insert(0, str(ROOT))
os.environ["KIVY_NO_ARGS"] = "1"

from kivy.tools.packaging.pyinstaller_hooks import get_deps_minimal, hookspath, runtime_hooks  # noqa: E402
from kivymd import hooks_path as kivymd_hooks_path  # noqa: E402

from PyInstaller.utils.hooks import collect_data_files, collect_submodules  # noqa: E402

from ytdl import APP_NAME  # noqa: E402

ONEFILE = os.environ.get("YTDL_ONEFILE") == "1"
CONSOLE = os.environ.get("YTDL_CONSOLE") == "1"
IS_WINDOWS = sys.platform.startswith("win")

# Provedores do Kivy: SDL2 para janela/texto/áudio e Pillow para imagens
# (miniaturas JPEG/WebP). Vídeo/câmera/ortografia não são usados.
kivy_deps = get_deps_minimal(video=None, camera=None, spelling=None)
# O KivyMD importa módulos por nome em tempo de execução (ex.: kivymd.icon_definitions,
# usado por TODOS os ícones). Sem isto o app congelado abre sem ícones / quebra.
# kivymd.tools é só ferramental de desenvolvimento (puxa dependências extras).
kivymd_modules = collect_submodules("kivymd", filter=lambda name: not name.startswith("kivymd.tools"))

hidden = list(kivy_deps.get("hiddenimports", [])) + kivymd_modules + [
    "kivy.core.image.img_pil",
    # Carregados sob demanda dentro de funções:
    "ytdl.core.ytdlp_service",
    "ytdl.core.fake_service",
]

a = Analysis(  # noqa: F821
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=kivy_deps.get("binaries", []),
    datas=[
        (str(ROOT / "ytdl" / "assets"), "ytdl/assets"),
        (str(ROOT / "ytdl" / "ui" / "kv"), "ytdl/ui/kv"),
    ] + collect_data_files("kivymd"),   # fontes, imagens E shaders GLSL (o hook oficial omite os .glsl)
    hiddenimports=hidden,
    # kivymd_hooks_path: fontes/ícones do KivyMD.  O yt-dlp registra o próprio hook
    # (inclui extratores e os scripts JS do yt-dlp-ejs) via entry point do PyInstaller.
    hookspath=hookspath() + [kivymd_hooks_path],
    runtime_hooks=runtime_hooks(),
    excludes=list(kivy_deps.get("excludes", [])) + ["tkinter", "pytest", "jnius", "android"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

_icon = ROOT / "ytdl" / "assets" / "icon.ico"
common = dict(
    name=APP_NAME,
    debug=False,
    strip=False,
    upx=False,                       # UPX aumenta falsos positivos de antivírus
    console=CONSOLE or not IS_WINDOWS,
    icon=str(_icon) if IS_WINDOWS and _icon.exists() else None,
)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **common)  # noqa: F821
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **common)  # noqa: F821
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=APP_NAME)  # noqa: F821
