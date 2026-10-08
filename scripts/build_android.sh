#!/usr/bin/env bash
# =============================================================================
# Gera o APK do YTDL com o Buildozer.   FUNCIONA SOMENTE EM LINUX (ou WSL2).
#
#   ./scripts/build_android.sh --install-deps   # 1ª vez: instala pacotes do sistema (sudo)
#   ./scripts/build_android.sh                  # APK debug  -> bin/*.apk
#   ./scripts/build_android.sh release          # APK release (sem assinatura)
#   ./scripts/build_android.sh clean            # limpa o build (use ao mudar "requirements")
#   ./scripts/build_android.sh logcat           # log do celular via USB (adb)
#
# Windows: rode DENTRO do WSL2 (Ubuntu). Veja a seção "Android no Windows" do README.
# A 1ª compilação baixa SDK/NDK (~3 GB) e leva 20-40 min; as seguintes são rápidas.
# =============================================================================
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$(pwd)"
VENV="$ROOT/.venv-android"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERRO: o Buildozer só funciona em Linux. No Windows use o WSL2 (veja o README)." >&2
  exit 1
fi

if [[ "$ROOT" == /mnt/* ]]; then
  echo "AVISO: o projeto está em $ROOT (disco do Windows montado no WSL)." >&2
  echo "       O build fica MUITO lento e pode falhar por permissões de arquivo." >&2
  echo "       Copie o projeto para o disco do Linux:  cp -r \"$ROOT\" ~/ytdl && cd ~/ytdl" >&2
  [[ "${YTDL_ALLOW_MNT:-0}" == "1" ]] || { echo "       (defina YTDL_ALLOW_MNT=1 para ignorar este aviso)" >&2; exit 1; }
fi

install_deps() {
  echo ">> Instalando pacotes do sistema (pede sudo)..."
  sudo apt-get update
  # libtinfo5 só existe no Ubuntu <= 22.04; no 24.04 o libncurses-dev basta.
  extra=""
  if apt-cache show libtinfo5 >/dev/null 2>&1; then extra="libtinfo5"; fi
  sudo apt-get install -y \
    git zip unzip openjdk-17-jdk python3 python3-pip python3-venv python3-dev \
    autoconf automake libtool libltdl-dev pkg-config build-essential ccache cmake \
    zlib1g-dev libncurses-dev libffi-dev libssl-dev lld ca-certificates $extra
  echo ">> Pacotes instalados."
}

ensure_buildozer() {
  if [[ ! -x "$VENV/bin/buildozer" ]]; then
    echo ">> Criando ambiente virtual do Buildozer em $VENV"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --upgrade pip wheel
    # Cython/setuptools de versões compatíveis com o recipe do Kivy 2.3.1 são
    # instalados pelo próprio p4a no hostpython; aqui só precisamos do buildozer.
    "$VENV/bin/pip" install "buildozer==1.6.0"
  fi
}

case "${1:-debug}" in
  --install-deps) install_deps; exit 0 ;;
  logcat)
    command -v adb >/dev/null || { echo "adb não encontrado (sudo apt install adb)"; exit 1; }
    exec adb logcat -s python ;;
  clean)  ensure_buildozer; exec "$VENV/bin/buildozer" android clean ;;
  debug|release)
    ensure_buildozer
    mode="$1"
    export PATH="$VENV/bin:$PATH"
    # Se rodar como root, o buildozer pede confirmação (warn_on_root no spec). Prefira usuário comum.
    "$VENV/bin/buildozer" -v android "$mode"
    echo
    echo ">> APK(s) gerado(s):"
    ls -lh "$ROOT"/bin/*.apk
    ;;
  *) echo "Uso: $0 [--install-deps | debug | release | clean | logcat]" >&2; exit 2 ;;
esac
