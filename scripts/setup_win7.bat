@echo off
REM ============================================================================
REM  Prepara o ambiente do perfil LEGADO (Windows 7/8) com Python 3.8.
REM
REM  Pré-requisitos (instale ANTES):
REM    * Python 3.8.10 (64 ou 32 bits)  https://www.python.org/downloads/release/python-3810/
REM      (marque "Add python.exe to PATH"; o 3.8.10 é o ULTIMO que roda no Windows 7)
REM    * Windows 7 SP1 + atualização "Universal C Runtime" (KB2999226) e VC++ 2015-2019
REM
REM  Uso (na raiz do projeto):   scripts\setup_win7.bat
REM  Depois:                     .venv-win7\Scripts\activate  &  python scripts\build_desktop.py
REM
REM  AVISO: este script NÃO foi executado em Windows pelo autor (o ambiente de
REM  desenvolvimento era Linux). Os mesmos passos foram verificados com Python 3.8 no
REM  Linux; se algo falhar no Windows, leia a seção "Windows 7" do README.
REM ============================================================================
setlocal
cd /d "%~dp0\.."

py -3.8 --version >nul 2>&1 || (echo ERRO: Python 3.8 nao encontrado. Instale o 3.8.10. & exit /b 1)

if not exist .venv-win7 (
  echo [1/5] Criando ambiente virtual .venv-win7
  py -3.8 -m venv .venv-win7 || exit /b 1
)
call .venv-win7\Scripts\activate.bat

echo [2/5] Atualizando pip
python -m pip install --upgrade "pip<25" setuptools wheel || exit /b 1

echo [3/5] Instalando dependencias (requirements-win7.txt)
pip install -r requirements-win7.txt || exit /b 1

echo [4/5] Instalando KivyMD 2.0.0 sem dependencias (evita materialshapes/pycairo)
pip install --no-deps kivymd==2.0.0 || exit /b 1

echo [5/5] materialyoucolor em modo Python puro (nao ha wheel para Python 3.8) + remendo
set MYCP_PURE_PYTHON=1
pip install --no-binary materialyoucolor "materialyoucolor==3.0.4" || exit /b 1
python scripts\win7_patch_materialyoucolor.py || exit /b 1

echo.
echo Pronto. Teste:   python main.py --demo
echo Gerar .exe:      python scripts\build_desktop.py
endlocal
