"""YTDL - Baixador de vídeos/áudios multiplataforma (Kivy + KivyMD + yt-dlp).

Este pacote contém TODO o código da aplicação. A estrutura é:

    ytdl/
    ├── core/      Lógica de negócio, SEM dependência de Kivy (testável e reutilizável)
    ├── ui/        Telas, widgets e arquivos .kv (Kivy / KivyMD)
    ├── assets/    Ícones e imagens
    ├── app.py     Classe do aplicativo (MDApp)
    ├── paths.py   Resolução de caminhos (dev / PyInstaller / Android)
    ├── logger.py  Configuração de logging
    └── ...
"""

# A versão é lida também pelo buildozer (version.regex no buildozer.spec):
# mantenha a atribuição abaixo em uma única linha, com aspas, começando na coluna 0.
__version__ = "0.2.0"
APP_NAME = "YTDL"
