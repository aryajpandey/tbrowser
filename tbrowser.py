
import sys
import os
import time
import urllib.parse
import json
from typing import Optional

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history", "browser_history.json")

def read_asset(filename: str) -> str:
    path = os.path.join(ASSETS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<html><body><p>Failed to load asset: {}</p></body></html>".format(filename)

# --- Guarded dual-imports for PyQt6 / PyQt5 compatibility --------------------
USING_QT6 = False

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
    from PyQt5.QtGui import QAction, QIcon, QKeySequence, QShortcut  # <-- QShortcut here!
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
        QLineEdit, QTabBar, QStackedWidget, QToolButton, QFileDialog, QLabel,
        QStyle, QMessageBox, QSizePolicy
    )
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage

# -----------------------------------------------------------------------------

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


class BrowserTab(QWidget):
    def __init__(self, parent=None, url: QUrl = QUrl("about:blank"), private: bool = False):
        super().__init__(parent)
        self.private = private
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.view = QWebEngineView(self)

        # Set up a private/off-the-record profile when requested
        if private:
            profile = QWebEngineProfile(self.view)
            # Best-effort cross-version incognito:
            try:
                # Qt6 API
                profile.setOffTheRecord(True)  # type: ignore[attr-defined]
            except Exception:
                # Qt5 fallback: no persistent storage/cookies/cache
                try:
                    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)  # type: ignore
                except Exception:
                    pass
                try:
                    profile.setPersistentStoragePath('')
                    profile.setCachePath('')
                except Exception:
                    pass
            page = QWebEnginePage(profile, self.view)
            self.view.setPage(page)

        self.layout.addWidget(self.view)
        self.view.setUrl(url)

    def title(self) -> str:
        try:
            return self.view.title() or "New Tab"
        except Exception:
            return "New Tab"

    def url(self) -> QUrl:
        return self.view.url()

    def is_private(self) -> bool:
        return self.private


class CommandPalette(QFrame):
    """Translucent bottom command palette with a single-line input."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CommandPalette")
        self.setAutoFillBackground(False)

        self.setStyleSheet("""
            QFrame#CommandPalette {
                background-color: rgba(10, 10, 10, 180);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 10px;
            }
            QLineEdit {
                background: transparent;
                color: white;
                font-family: "Courier New", monospace;
                font-size: 16px;
                padding: 10px 14px;
                border: none;
                selection-background-color: rgba(255,255,255,50);
            }
        """)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed if USING_QT6 else QSizePolicy.Fixed)

        self.input = QLineEdit(self)
        self.input.setPlaceholderText("/nt:<url> | /pt:<url> | /nw | /hist | /help | /capture")
        self.input.returnPressed.connect(self._on_return)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.addWidget(self.input)

        self.hide()

    def _on_return(self):
        text = self.input.text().strip()
        if self.parent() and hasattr(self.parent(), "handle_command"):
            getattr(self.parent(), "handle_command")(text)
        self.input.clear()
        self.hide()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.input.setFocus()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            # Width ~ 70% of window, height ~ 56 px
            pw = self.parent().width() if self.parent() else 800
            ph = self.parent().height() if self.parent() else 600
            w = int(pw * 0.7)
            h = 56
            x = int((pw - w) / 2)
            y = ph - h - 70  # float above bottom bar
            self.setGeometry(x, y, w, h)
            self.show()
            self.input.setFocus()
            self.input.setText("/")  # Always start with "/" when palette opens

    def keyPressEvent(self, event):
        # Close palette on Escape key
        if event.key() == Qt.Key.Key_Escape if USING_QT6 else Qt.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)


class MainWindow(QMainWindow):
    windows = []

    def _load_history(self):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_history(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    existing_history = json.load(f)
            except Exception:
                existing_history = []
            urls = set(entry["url"] for entry in existing_history)
            merged_history = existing_history[:]
            for entry in self.global_history:
                if entry["url"] not in urls:
                    merged_history.append(entry)
                    urls.add(entry["url"])
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(merged_history, f)
        except Exception:
            pass
    def go_back(self):
        tab = self.current_tab()
        if tab:
            tab.view.back()
    
    def go_forward(self):
        tab = self.current_tab()
        if tab:
            tab.view.forward()
    
    def reload_page(self):
        tab = self.current_tab()
        if tab:
            tab.view.reload()

    def handle_command(self, text: str):
        if not text.startswith("/"):
            QMessageBox.information(self, "Command", "Commands must start with '/'.")
            return

        parts = text[1:].split(":", 1)
        cmd = parts[0].strip().lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "nt":
            # If no argument, show new_tab.html
            if not arg:
                new_tab_html = read_asset("browser_pages/new_tab.html")
                self.new_tab(QUrl("about:blank"), private=False)
                tab = self.current_tab()
                if tab:
                    tab.view.setHtml(new_tab_html, QUrl("about:blank"))
            else:
                url = to_qurl(arg)
                self.new_tab(url, private=False)
                
        elif cmd == "pt":
            url = to_qurl(arg or "about:blank")
            self.new_tab(url, private=True)
        elif cmd == "t":
            url = to_qurl(arg or "about:blank")
            tab = self.current_tab()
            if tab:
                tab.view.setUrl(url)
            else:
                self.new_tab(url, private=False)
        elif cmd == "nw":
            win = MainWindow()
            MainWindow.windows.append(win)
            win.show()
        elif cmd == "s":
            # /s:<text> - search in current tab
            query = urllib.parse.quote(arg)
            url = QUrl(f"https://www.google.com/search?q={query}")
            tab = self.current_tab()
            if tab:
                tab.view.setUrl(url)
            else:
                self.new_tab(url, private=False)
        elif cmd == "ts":
            # /ts:<text> - search in new tab
            query = urllib.parse.quote(arg)
            url = QUrl(f"https://www.google.com/search?q={query}")
            self.new_tab(url, private=False)

        elif cmd == "hist":
            self.open_history_tab()
        elif cmd == "help":
            self.open_help_tab()
        elif cmd == "capture":
            self.capture_screenshot()
        else:
            QMessageBox.warning(self, "Unknown command", f"Unrecognized command: {text}\nTry /help")

            
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TBrowser")
        self.resize(1200, 800)

        # Global (non-private) history
        self.global_history = self._load_history()

        # Central layout (stack for tabs + bottom bar)
        central = QWidget(self)
        self.setCentralWidget(central)
        self.vbox = QVBoxLayout(central)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(0)

        # Stack hosts the tab widgets
        self.stack = QStackedWidget(self)
        self.vbox.addWidget(self.stack, 1)

        # Bottom bar with navigation + tabs
        self.bottom = QWidget(self)
        self.bottom.setObjectName("BottomBar")
        self.bottom.setStyleSheet("""
            QWidget#BottomBar {
                background: #111;
                border-top: 1px solid #333;
            }
            QToolButton {
                color: #ddd;
                border: none;
                padding: 8px 10px;
            }
            QToolButton:hover { background: #1b1b1b; }
            QTabBar::tab {
                background: #1a1a1a;
                color: #eee;
                padding: 8px 12px;
                margin: 6px 2px;
                border-radius: 6px;
            }
            QTabBar::tab:selected { background: #2a2a2a; }
            QTabBar::close-button {
                image: none;
                width: 0px; height: 0px; /* hide by default */
            }
        """)
        h = QHBoxLayout(self.bottom)
        h.setContentsMargins(8, 0, 8, 0)
        h.setSpacing(4)

        self.btn_back = QToolButton(self.bottom)
        self.btn_back.setIcon(resource_icon("back"))
        self.btn_back.setToolTip("Back (Ctrl/Cmd + Left)")
        self.btn_back.clicked.connect(self.go_back)

        self.btn_forward = QToolButton(self.bottom)
        self.btn_forward.setIcon(resource_icon("forward"))
        self.btn_forward.setToolTip("Forward (Ctrl/Cmd + Right)")
        self.btn_forward.clicked.connect(self.go_forward)

        self.btn_reload = QToolButton(self.bottom)
        self.btn_reload.setIcon(resource_icon("reload"))
        self.btn_reload.setToolTip("Reload (Ctrl/Cmd + R)")
        self.btn_reload.clicked.connect(self.reload_page)

        # Spacer between nav and tabs
        spacer = QWidget(self.bottom)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred if USING_QT6 else QSizePolicy.Preferred)

        self.tabbar = QTabBar(self.bottom)
        self.tabbar.setMovable(True)
        self.tabbar.setTabsClosable(True)
        self.tabbar.currentChanged.connect(self.on_tab_changed)
        self.tabbar.tabCloseRequested.connect(self.close_tab)

        h.addWidget(self.btn_back)
        h.addWidget(self.btn_forward)
        h.addWidget(self.btn_reload)
        h.addWidget(spacer, 1)
        h.addWidget(self.tabbar, 5)

        self.vbox.addWidget(self.bottom, 0)

        # Slash Command Palette overlay
        self.palette = CommandPalette(self)

        # Shortcuts
        self._make_shortcuts()
        QApplication.instance().installEventFilter(self)

        # Start with one tab
        new_tab_html = read_asset("browser_pages/new_tab.html")
        self.new_tab(QUrl("about:blank"))
        tab = self.current_tab()
        if tab:
            tab.view.setHtml(new_tab_html, QUrl("about:blank"))



    # --- Shortcuts -----------------------------------------------------------
    def _make_shortcuts(self):
        self._shortcuts = []  # keep references so shortcuts don't get garbage-collected

        def sc(seq, handler, context=None):
            s = QShortcut(QKeySequence(seq), self, activated=handler)
            if context is not None:
                s.setContext(context)
            self._shortcuts.append(s)
            return s

        # Reload
        sc("Ctrl+R", self.reload_page)
        sc("Meta+R", self.reload_page)  # macOS

        # Back/Forward
        sc("Ctrl+Left", self.go_back)
        sc("Meta+Left", self.go_back)
        sc("Ctrl+Right", self.go_forward)
        sc("Meta+Right", self.go_forward)

        # Toggle palette with "/"
        sc("/", self.palette.toggle)

        # Close current tab
        sc("Ctrl+W", self.close_current_tab)
        sc("Meta+W", self.close_current_tab)

        # History
        sc("Ctrl+H", self.open_history_tab, Qt.ShortcutContext.ApplicationShortcut)
        sc("Meta+Y", self.open_history_tab, Qt.ShortcutContext.ApplicationShortcut)

        # Tab switching (will still back up with the event filter)
        sc("Ctrl+Tab", self.next_tab, Qt.ShortcutContext.ApplicationShortcut)
        sc("Ctrl+Shift+Tab", self.prev_tab, Qt.ShortcutContext.ApplicationShortcut)


    # --- Tabs management -----------------------------------------------------
    def new_tab(self, url: QUrl, private: bool = False) -> int:
        tab = BrowserTab(self, url=url, private=private)
        idx = self.stack.addWidget(tab)
        label = "Private" if private else "New Tab"
        tindex = self.tabbar.addTab(label)
        if private:
            # Purple label to indicate private
            self.tabbar.setTabTextColor(tindex, Qt.GlobalColor.magenta if USING_QT6 else Qt.magenta)
        self.tabbar.setCurrentIndex(tindex)
        self.stack.setCurrentIndex(idx)

        # Wiring signals to update tab text + history
        tab.view.titleChanged.connect(lambda _=None, t=tab: self._update_tab_title(t))
        tab.view.urlChanged.connect(lambda _=None, t=tab: self._on_url_changed(t))
        tab.view.loadFinished.connect(lambda ok, t=tab: self._on_load_finished(t, ok))

        return tindex

    def close_tab(self, index: int):
        if self.tabbar.count() <= 1:
            # Keep at least one tab open
            self.reload_page()
            return
        w = self.stack.widget(index)
        self.stack.removeWidget(w)
        w.deleteLater()
        self.tabbar.removeTab(index)
        # Ensure a valid current index
        if self.tabbar.count() > 0:
            self.tabbar.setCurrentIndex(max(0, index - 1))
    
    def close_current_tab(self):
        idx = self.tabbar.currentIndex()
        if idx != -1:
            self.close_tab(idx)

    def on_tab_changed(self, index: int):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def current_tab(self) -> Optional[BrowserTab]:
        idx = self.tabbar.currentIndex()
        if 0 <= idx < self.stack.count():
            w = self.stack.widget(idx)
            if isinstance(w, BrowserTab):
                return w
        return None

    def next_tab(self):
        count = self.tabbar.count()
        if count > 1:
            current = self.tabbar.currentIndex()
            next_idx = (current + 1) % count
            self.tabbar.setCurrentIndex(next_idx)
    
    def prev_tab(self):
        count = self.tabbar.count()
        if count > 1:
            current = self.tabbar.currentIndex()
            prev_idx = (current - 1) % count
            self.tabbar.setCurrentIndex(prev_idx)
            
    def eventFilter(self, obj, event):
        try:
            if event.type() == (QEvent.Type.KeyPress if USING_QT6 else QEvent.KeyPress):
                key = event.key()
                mods = event.modifiers()

                ctrl = bool(mods & (Qt.KeyboardModifier.ControlModifier if USING_QT6 else Qt.ControlModifier))
                shift = bool(mods & (Qt.KeyboardModifier.ShiftModifier if USING_QT6 else Qt.ShiftModifier))
                is_tab = key == (Qt.Key.Key_Tab if USING_QT6 else Qt.Key_Tab)
                is_backtab = key == (Qt.Key.Key_Backtab if USING_QT6 else Qt.Key_Backtab)

                if ctrl and (is_tab or is_backtab):
                    if shift or is_backtab:
                        self.prev_tab()
                    else:
                        self.next_tab()
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _update_tab_title(self, tab: BrowserTab):
        try:
            idx = self.stack.indexOf(tab)
            if idx != -1:
                title = tab.title()
                # Keep titles reasonably short
                if len(title) > 28:
                    title = title[:28] + "…"
                self.tabbar.setTabText(idx, title)
        except Exception:
            pass

    def _on_url_changed(self, tab: BrowserTab):
        # Could reflect URL elsewhere if we add an address bar in future
        pass

    def _on_load_finished(self, tab: BrowserTab, ok: bool):
        # Record into global (non-private) history
        if ok and not tab.is_private():
            url = tab.url().toString()
            title = tab.title() or url
            # De-duplicate consecutive entries for same URL
            entry = {"title": title, "url": url, "timestamp": time.time()}
            # Load latest history from file before appending
            latest_history = self._load_history()
            # Only append if not duplicate of last entry in file
            if not latest_history or latest_history[-1].get("url") != url:
                latest_history.append(entry)
                self.global_history = latest_history
                self._save_history()

    def _save_history(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    existing_history = json.load(f)
            except Exception:
                existing_history = []
            urls = set(entry["url"] for entry in existing_history)
            merged_history = existing_history[:]
            for entry in self.global_history:
                if entry["url"] not in urls:
                    merged_history.append(entry)
                    urls.add(entry["url"])
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(merged_history, f)
        except Exception:
            pass

    def closeEvent(self, event):
        if self.global_history:
            self._save_history()
        super().closeEvent(event)

    def open_history_tab(self):
        html = read_asset("browser_pages/history.html")
        # Use current session history for dynamic updates
        history = self.global_history
        history_items = ""
        for entry in reversed(history):
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry["timestamp"]))
            history_items += f'<li><a href="{entry["url"]}">{entry["title"]}</a> <small>{ts}</small></li>\n'
        if history_items:
            html = html.replace("<!-- HISTORY_ITEMS -->", f"<ul>{history_items}</ul>")
        else:
            html = html.replace("<!-- HISTORY_ITEMS -->", "<p><em>No history yet (private tabs are excluded).</em></p>")
        tab_index = self.new_tab(QUrl("about:blank"), private=False)
        tab = self.current_tab()
        if tab:
            tab.view.setHtml(html, QUrl("about:blank"))
            self.tabbar.setTabText(tab_index, "History")

    def open_help_tab(self):
        help_html = read_asset("browser_pages/help.html")
        tab_index = self.new_tab(QUrl("about:blank"), private=False)
        tab = self.current_tab()
        if tab:
            tab.view.setHtml(help_html, QUrl("about:blank"))
            self.tabbar.setTabText(tab_index, "Help")

    def capture_screenshot(self):
        tab = self.current_tab()
        if not tab:
            return
        # Grab the visible widget area
        pix = tab.view.grab()
        if pix.isNull():
            QMessageBox.warning(self, "Screenshot", "Failed to capture screenshot.")
            return

        default_name = time.strftime("tbrowser_%Y%m%d_%H%M%S.png")
        # Ask user where to save
        path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", default_name, "PNG Image (*.png)")
        if not path:
            return
        saved = pix.save(path, "PNG")
        if saved:
            self.statusBar().showMessage(f"Saved screenshot: {path}", 5000)
        else:
            QMessageBox.warning(self, "Screenshot", "Failed to save screenshot.")

    # --- Events --------------------------------------------------------------
    def keyPressEvent(self, event):
        # Give global "/" toggle even when a web view is focused
        try:
            if event.text() == "/":
                self.palette.toggle()
                event.accept()
                return
        except Exception:
            pass
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        # Keep palette docked above bottom bar when visible
        if self.palette.isVisible():
            self.palette.toggle()  # will recompute geometry
            self.palette.toggle()
        super().resizeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TBrowser")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
   


if __name__ == "__main__":
    main()
