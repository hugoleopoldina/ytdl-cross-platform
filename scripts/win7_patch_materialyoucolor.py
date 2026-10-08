"""Remendo para rodar o ``materialyoucolor`` 3.0.x no Python 3.8 (Windows 7).

Problema: o pacote declara suporte a Python 3.7+, mas anotações como
``list[float]`` são avaliadas em tempo de execução e exigem Python 3.9:

    TypeError: 'type' object is not subscriptable

Além disso, não existem wheels para cp38, então ele é instalado em modo
Python puro (``MYCP_PURE_PYTHON=1``). Este script adiciona
``from __future__ import annotations`` (anotações preguiçosas, PEP 563) a cada
arquivo do pacote que ainda não o tem. É idempotente e só altera o texto das
anotações; não muda comportamento.

Uso (com o Python 3.8 do ambiente virtual do Windows 7):

    python scripts/win7_patch_materialyoucolor.py
"""
import importlib.util
import re
import sys
from pathlib import Path

FUTURE = "from __future__ import annotations\n"


def main() -> int:
    spec = importlib.util.find_spec("materialyoucolor")  # NÃO importa (falharia)
    if spec is None or not spec.submodule_search_locations:
        print("materialyoucolor não está instalado neste Python.")
        return 1
    root = Path(list(spec.submodule_search_locations)[0])
    patched = 0
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from __future__ import annotations" in text:
            continue
        # O __future__ precisa vir após o docstring do módulo (se houver) e comentários.
        match = re.match(r'(\s*(?:#[^\n]*\n\s*)*(?:(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')\s*\n)?)', text)
        head = match.group(1) if match else ""
        path.write_text(head + FUTURE + text[len(head):], encoding="utf-8")
        patched += 1
    print(f"{patched} arquivo(s) remendado(s) em {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
