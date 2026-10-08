"""Estrutura raiz: gerenciador de telas + barra de navegação inferior."""
from __future__ import annotations

from kivy.properties import StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.navigationbar import MDNavigationItem


class NavItem(MDNavigationItem):
    """Item da barra inferior. ``target`` é o nome da tela de destino."""

    icon = StringProperty()
    text = StringProperty()
    target = StringProperty()


class Shell(MDBoxLayout):
    """Raiz da interface (aparência em ``kv/shell.kv``)."""
