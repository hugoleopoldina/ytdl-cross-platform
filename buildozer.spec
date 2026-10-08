# =============================================================================
# buildozer.spec - APK do YTDL (somente em Linux / WSL2; veja o README)
#
#   buildozer android debug           -> bin/ytdl-<versão>-<arch>-debug.apk
#   buildozer android release         -> APK sem assinatura (assine antes de distribuir)
#   buildozer android clean           -> limpa o build (use ao mudar "requirements")
#
# Versões fixadas e VERIFICADAS (não use "master"/".dev" como no projeto antigo):
#   python-for-android  v2026.05.09   (p4a.branch)
#   Python alvo         3.11.9        (o p4a usaria 3.14 por padrão; o Kivy 2.3.1 não suporta)
#   Kivy 2.3.1  /  KivyMD 2.0.0  /  materialyoucolor 3.0.4
# =============================================================================
[app]

title = YTDL
package.name = ytdl
package.domain = org.youtubedl

# Raiz do projeto: main.py fica aqui e o pacote "ytdl/" vai junto. Nada é copiado:
# o buildozer só empacota o que passar pelos filtros abaixo.
source.dir = .
source.include_exts = py,png,jpg,kv,json
source.exclude_dirs = tests, docs, demo, scripts, build, dist, bin, venv, .venv, env, .git, .github, .buildozer, __pycache__
source.exclude_patterns = ytdl.spec, requirements*.txt, README.md

# A versão vem de ytdl/__init__.py (fonte única de verdade, usada também pelo app).
version.regex = (?m)^__version__ = ['"](.*)['"]
version.filename = %(source.dir)s/ytdl/__init__.py

# -----------------------------------------------------------------------------
# Dependências. O p4a instala módulos Python puros com "pip --no-deps": toda
# dependência precisa estar listada AQUI (por isso a lista é explícita).
#
#  * python3/hostpython3 ...... fixos em 3.11.9 (precisam ser IGUAIS)
#  * materialyoucolor==3.0.4 .. OBRIGATÓRIO: o recipe padrão (2.0.10) é incompatível
#                               com o KivyMD 2.0 ("color_spec" não existe nele)
#  * NÃO inclua materialshapes/pycairo: só servem ao widget MDLoadingIndicator, que o
#    app não usa, e pycairo não tem recipe estável no Android
#  * asynckivy/asyncgui/exceptiongroup: dependências do KivyMD
#  * yt-dlp ..................... sem versão: pega a mais recente a cada build (o YouTube
#                               muda toda semana). Fixe aqui se precisar reproduzir um build
#  * certifi/filetype/... ....... já entram pelo recipe do Kivy
# -----------------------------------------------------------------------------
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.1,kivymd==2.0.0,materialyoucolor==3.0.4,asynckivy==0.6.4,asyncgui==0.6.3,exceptiongroup,pillow,pyjnius,android,certifi,mutagen,yt-dlp,androidstorage4kivy,docutils,pygments

presplash.filename = %(source.dir)s/ytdl/assets/presplash.png
icon.filename = %(source.dir)s/ytdl/assets/icon.png

orientation = portrait
fullscreen = 0

# Mostra o log do Python no "adb logcat -s python" (o app também grava ytdl.log).
android.logcat_filters = *:S python:D

# ----------------------------------------------------------------------------- #
# Android
# ----------------------------------------------------------------------------- #
# INTERNET ........................ busca e download
# WRITE_EXTERNAL_STORAGE (<=28) ... Android 9 ou anterior gravar em Download/
# READ_EXTERNAL_STORAGE (<=32) .... exigido pelo androidstorage4kivy no Android 10-12
# (Android 10+ grava em Download/ via MediaStore, sem permissão adicional.)
android.permissions = INTERNET, (name=android.permission.WRITE_EXTERNAL_STORAGE;maxSdkVersion=28), (name=android.permission.READ_EXTERNAL_STORAGE;maxSdkVersion=32)

android.api = 34
android.minapi = 24
android.ndk = 28c
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.private_storage = True
android.allow_backup = True
android.debug_artifact = apk

# Versão do python-for-android FIXA (reprodutível). Troque por "master" só para testar novidades.
p4a.branch = v2026.05.09

# -----------------------------------------------------------------------------
[buildozer]
log_level = 2
warn_on_root = 1
