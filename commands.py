from typing import Callable, Dict, Optional
import json, os, urllib
from pathlib import Path
from constants import COMMANDS_JSON
from utils import to_qurl, read_asset

try:
    from PyQt6.QtCore import Qt, QUrl, QSize, QEvent
    from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut  # <-- QShortcut here!
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
        QLineEdit, QTabBar, QStackedWidget, QToolButton, QFileDialog, QLabel,
        QStyle, QMessageBox, QSizePolicy
    )
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
    USING_QT6 = True
except Exception:
    from PyQt5.QtCore import Qt, QUrl, QSize, QEvent



REGISTRY: Dict[str, Callable[[object, str], None]] = {}

def register_command(name: str, fn: Callable[[object, str], None]) -> None:
    REGISTRY[name.lower()] = fn

def unregister_command(name: str) -> None:
    REGISTRY.pop(name.lower(), None)

def command_handler(window, text: str, new_window_factory=None) -> None:
    if not text.startswith("/"):
        QMessageBox.information(window, "Command", "Commands must start with '/'.")
        return

    parts = text[1:].split(":", 1)
    cmd = parts[0].strip().lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    # 1) User / plugin commands first
    if cmd in REGISTRY:
        REGISTRY[cmd](window, arg)
        return

    # 2) Built-ins
    if cmd == "nt":
        if not arg:
            new_tab_html = read_asset("browser_pages/new_tab.html")
            window.new_tab(QUrl("about:blank"), private=False)
            tab = window.current_tab()
            if tab:
                tab.view.setHtml(new_tab_html, QUrl("about:blank"))
        else:
            url = to_qurl(arg)
            window.new_tab(url, private=False)

    elif cmd == "pt":
        if not arg:
            new_ptab_html = read_asset("browser_pages/new-ptab.html")
            window.new_tab(QUrl("about:blank"), private=True)
            tab = window.current_tab()
            if tab:
                tab.view.setHtml(new_ptab_html, QUrl("about:blank"))
        else:
            url = to_qurl(arg)
            tab = window.new_tab(QUrl("about:blank"), private=True)
            if tab:
                tab.view.setUrl(url)

    elif cmd == "t":
        url = to_qurl(arg or "about:blank")
        tab = window.current_tab()
        if tab:
            tab.view.setUrl(url)
        else:
            window.new_tab(url, private=False)

    elif cmd == "nw":
        if new_window_factory is None:
            QMessageBox.warning(window, "Unavailable", "New window command is not wired up.")
            return
        win = new_window_factory()
        win.show()

    elif cmd == "s":
        query = urllib.parse.quote(arg)
        url = QUrl(f"https://www.google.com/search?q={query}")
        tab = window.current_tab()
        if tab:
            tab.view.setUrl(url)
        else:
            window.new_tab(url, private=False)

    elif cmd == "ts":
        query = urllib.parse.quote(arg)
        url = QUrl(f"https://www.google.com/search?q={query}")
        window.new_tab(url, private=False)

    elif cmd == "hist":
        window.open_history_tab()

    elif cmd == "help":
        window.open_help_tab()
    
    elif cmd == "commands":
        window.open_commands_tab()

    elif cmd == "capture":
        window.capture_screenshot()

    else:
        QMessageBox.warning(window, "Unknown command",
                            f"Unrecognized command: {text}\nTry /help")

def _url_template_handler(template: str):
    def _fn(window, arg: str):
        q = urllib.parse.quote(arg or "")
        url = QUrl(template.format(q=q))
        # open in a new normal tab; you could add a convention for private
        tab = window.current_tab()
        if tab:
            tab.view.setUrl(url)
        else:
            window.new_tab(url, private=False)
    return _fn

def load_user_commands() -> None:
    if not COMMANDS_JSON.exists():
        return
    try:
        data = json.loads(COMMANDS_JSON.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for name, template in data.items():
                if isinstance(name, str) and isinstance(template, str) and "{q}" in template:
                    register_command(name, _url_template_handler(template))
    except Exception as e:
        print("Failed to load user commands:", e)

def _save_user_command(name: str, template: str) -> None:
    data = {}
    if COMMANDS_JSON.exists():
        try:
            data = json.loads(COMMANDS_JSON.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
    data[name] = template
    COMMANDS_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _alias_cmd(window, arg: str):
    """
    Syntax: /alias:name=template
    Examples:
      /alias:yt=https://www.youtube.com/results?search_query={q}
      /alias:gh=https://github.com
    """
    try:
        name, template = arg.split("=", 1)
        name = name.strip().lower()
        template = template.strip()
        if not name:
            raise ValueError

        if "{q}" in template:
            # Search-style alias
            handler = _url_template_handler(template)
        else:
            # Direct URL alias
            def handler(window, arg2):
                if arg2:  # Append if user gives extra path
                    if not template.endswith("/") and not arg2.startswith("/"):
                        url = f"{template}/{arg2}"
                    else:
                        url = template + arg2
                else:
                    url = template
                window.new_tab(to_qurl(url), private=False)

        register_command(name, handler)
        _save_user_command(name, template)
        QMessageBox.information(window, "Mapped",
                                f"/{name} -> {template}")
    except Exception:
        QMessageBox.warning(window, "Map error",
                            "Usage: /map:name=https://site/")


def _unalias_cmd(window, arg: str):
    name = (arg or "").strip().lower()
    if not name:
        QMessageBox.warning(window, "Unalias", "Usage: /unalias:name")
        return
    unregister_command(name)
    # update file
    data = {}
    if COMMANDS_JSON.exists():
        try:
            data = json.loads(COMMANDS_JSON.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
    if name in data:
        data.pop(name)
        COMMANDS_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    QMessageBox.information(window, "Unalias", f"Removed /{name}")

register_command("map", _alias_cmd)
register_command("unmap", _unalias_cmd)