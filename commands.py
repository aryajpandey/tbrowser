import os

import urllib
from constants import ASSETS_DIR, HISTORY_FILE
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

def to_qurl(s: str) -> QUrl:
    """Smartly coerce a user string into a QUrl (URL or search)."""
    s = (s or "").strip()
    if not s:
        return QUrl("about:blank")
    # If it looks like a URL without scheme, add https://
    if "://" not in s and " " not in s and "." in s:
        s = "https://" + s
    # If it has spaces and no scheme, treat as search query
    if "://" not in s:
        s = "https://www.google.com/search?q=" + urllib.parse.quote(s)
    return QUrl(s)

def read_asset(filename: str) -> str:
    path = os.path.join(ASSETS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<html><body><p>Failed to load asset: {}</p></body></html>".format(filename)

def command_handler(window, text: str, new_window_factory=None) -> None:
    if not text.startswith("/"):
        QMessageBox.information(window, "Command", "Commands must start with '/'.")
        return

    parts = text[1:].split(":", 1)
    cmd = parts[0].strip().lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

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
        url = to_qurl(arg or "about:blank")
        window.new_tab(url, private=True)

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

    elif cmd == "capture":
        window.capture_screenshot()

    else:
        QMessageBox.warning(window, "Unknown command", f"Unrecognized command: {text}\nTry /help")