"""Fonte de sistema com cobertura ampla para títulos de vídeos.

Problema do app original: títulos com emoji, japonês, coreano, árabe etc.
apareciam como quadradinhos, porque a fonte Roboto do KivyMD não tem esses
glifos. A solução anterior era EMBUTIR a ``seguiemj.ttf`` da Microsoft, o que
**viola a licença** (EULA proíbe redistribuir). Aqui nenhuma fonte de terceiros
é embutida: procuramos uma fonte ampla JÁ INSTALADA no sistema do usuário e a
usamos só nos textos que vêm da internet (título/canal). Se nada for achado,
usa-se a Roboto padrão do KivyMD.

Observação: o Kivy renderiza em monocromático; emoji coloridos aparecem como
glifos de uma cor (ou quadrado, se a fonte não tiver o emoji).
"""
from __future__ import annotations

import os
from typing import Optional

from .logger import get_logger

log = get_logger("fonts")

# Ordem = preferência. Fontes com CJK primeiro (também cobrem latim e acentos).
_CANDIDATES = (
    # Android
    "/system/fonts/NotoSansCJK-Regular.ttc",
    "/system/fonts/NotoSansSC-Regular.otf",
    "/system/fonts/DroidSansFallback.ttf",
    "/system/fonts/DroidSansFallbackFull.ttf",
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/unifont/unifont.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    # Windows (Vista/7/10/11)
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\YuGothR.ttc",
    r"C:\Windows\Fonts\meiryo.ttc",
    r"C:\Windows\Fonts\segoeui.ttf",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
)


def find_content_font() -> Optional[str]:
    """Caminho da primeira fonte ampla instalada, ou None."""
    for path in _CANDIDATES:
        if os.path.isfile(path):
            log.info("Fonte de conteúdo: %s", path)
            return path
    log.info("Nenhuma fonte ampla encontrada; usando Roboto para títulos")
    return None
