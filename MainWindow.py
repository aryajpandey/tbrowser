import json
import os
import time
from typing import Optional

import urllib
from BrowserTab import BrowserTab
from cmd_palette import CommandPalette
from commands import command_handler
from shortcuts import shortcuts
from constants import ASSETS_DIR, HISTORY_FILE
from utils import to_qurl, read_asset, resource_icon

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


    
    
class MainWindow(QMainWindow):
    windows = []

    @classmethod
    def new_window(cls):
        w = cls()
        cls.windows.append(w)
        return w
    
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
        command_handler(self, text, new_window_factory=type(self).new_window)
    

            
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

    def _make_shortcuts(self):
        shortcuts(self)


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