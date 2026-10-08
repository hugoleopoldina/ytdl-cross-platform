"""Gera o executável de desktop (Windows ou Linux) com o PyInstaller.

    python scripts/build_desktop.py              # pasta dist/YTDL/ (recomendado)
    python scripts/build_desktop.py --onefile    # um único executável
    python scripts/build_desktop.py --console    # mantém console (Windows) p/ depurar

Rode no MESMO sistema operacional do alvo: o PyInstaller não faz
cross-compilation (para .exe use Windows; para Linux use Linux/WSL).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check_environment() -> None:
    print(f"Python {sys.version.split()[0]} em {sys.executable}")
    if sys.version_info >= (3, 14):
        sys.exit("ERRO: Python 3.14+ não é suportado (o Kivy 2.3.1 não tem wheels). Use 3.11.")
    missing = []
    for module in ("kivy", "kivymd", "yt_dlp", "mutagen", "PIL", "PyInstaller"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        sys.exit("ERRO: faltam módulos: " + ", ".join(missing) +
                 "\n      Rode: pip install -r requirements-dev.txt")


def ensure_icon() -> None:
    """Gera o .ico do Windows a partir do PNG, se ainda não existir."""
    ico = ROOT / "ytdl" / "assets" / "icon.ico"
    if ico.exists():
        return
    from PIL import Image
    Image.open(ROOT / "ytdl" / "assets" / "icon.png").convert("RGBA").save(
        ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("Ícone gerado:", ico)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--onefile", action="store_true", help="um único executável")
    parser.add_argument("--console", action="store_true", help="mantém a janela de console")
    parser.add_argument("--no-clean", action="store_true", help="reaproveita o cache do PyInstaller")
    args = parser.parse_args()

    check_environment()
    ensure_icon()
    env = dict(os.environ)
    env["YTDL_ONEFILE"] = "1" if args.onefile else "0"
    env["YTDL_CONSOLE"] = "1" if args.console else "0"
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm",
               "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build" / "pyinstaller"),
               str(ROOT / "ytdl.spec")]
    if not args.no_clean:
        command.insert(3, "--clean")
    print("Executando:", " ".join(command))
    code = subprocess.call(command, cwd=str(ROOT), env=env)
    if code:
        return code

    exe_name = "YTDL.exe" if sys.platform.startswith("win") else "YTDL"
    exe = ROOT / "dist" / ("" if args.onefile else "YTDL") / exe_name
    print("\nPronto:", exe if exe.exists() else "(não encontrado!)")
    return 0 if exe.exists() else 1


if __name__ == "__main__":
    sys.exit(main())
