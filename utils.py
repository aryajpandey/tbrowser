import os
import urllib
from constants import ASSETS_DIR


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

def resource_icon(name: str) -> QIcon:
    """Return a standard icon for given name or a fallback blank icon."""
    style = QApplication.instance().style()
    std_map = {
        "back": QStyle.StandardPixmap.SP_ArrowBack,
        "forward": QStyle.StandardPixmap.SP_ArrowForward,
        "reload": QStyle.StandardPixmap.SP_BrowserReload,
        "newtab": QStyle.StandardPixmap.SP_FileDialogNewFolder,
        "history": QStyle.StandardPixmap.SP_DirHomeIcon,
        "help": QStyle.StandardPixmap.SP_DialogHelpButton,
        "camera": QStyle.StandardPixmap.SP_ComputerIcon,
    }
    if name in std_map:
        return style.standardIcon(std_map[name])
    return QIcon()


def read_asset(filename: str) -> str:
    path = os.path.join(ASSETS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<html><body><p>Failed to load asset: {}</p></body></html>".format(filename)