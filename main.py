"""Ponto de entrada do YTDL.

Usado por TODOS os alvos, sem cópias nem ajustes de caminho:

* desenvolvimento ........ ``python main.py``
* PyInstaller (win/linux)  ``ytdl.spec`` aponta para este arquivo
* Android (buildozer) .... o p4a procura ``main.py`` na raiz do projeto

Opções de linha de comando (desktop):

``--debug``   logs detalhados (equivale a YTDL_LOG_LEVEL=DEBUG)
``--demo``    dados fictícios, sem internet (para testar a interface)
``--version`` mostra a versão e sai
"""
import argparse
import os
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ytdl", description="YTDL - baixador de mídia")
    parser.add_argument("--debug", action="store_true", help="logs detalhados")
    parser.add_argument("--demo", action="store_true", help="modo demonstração (sem rede)")
    parser.add_argument("--version", action="store_true", help="mostra a versão")
    # parse_known_args: o Android/PyInstaller podem injetar argumentos extras.
    args, _unknown = parser.parse_known_args(argv)

    if args.version:
        from ytdl import __version__
        print(__version__)
        return 0

    # O Kivy consome sys.argv por conta própria; desligamos para não conflitar
    # com o argparse acima. DEVE ser definido antes de qualquer import do kivy.
    os.environ["KIVY_NO_ARGS"] = "1"
    # PIL primeiro: lê WebP/JPEG sem depender do SDL2_image (miniaturas do YouTube).
    os.environ.setdefault("KIVY_IMAGE", "pil,sdl2")

    from ytdl.logger import setup_logging
    setup_logging("DEBUG" if args.debug else None)

    from ytdl.app import run
    run(demo=args.demo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
