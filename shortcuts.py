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

def shortcuts(self):
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
        sc("Ctrl+H", self.open_history_tab)
        sc("Meta+Shift+H", self.open_history_tab)

        # Tab switching (will still back up with the event filter)
        sc("Ctrl+Tab", self.next_tab)
        sc("Ctrl+Shift+Tab", self.prev_tab)
        
        # New tab
        sc("Ctrl+T", self.onew_tab)
        sc("Meta+T", self.onew_tab)
        
        # New private tab
        sc("Ctrl+Shift+P", self.onew_ptab)
        sc("Meta+Shift+P", self.onew_ptab)
        
        act_next = QAction(self)
        act_next.setShortcuts([QKeySequence("Ctrl+Tab")])
        act_next.triggered.connect(self.next_tab)
        self.addAction(act_next)

        act_prev = QAction(self)
        act_prev.setShortcuts([QKeySequence("Ctrl+Shift+Tab")])
        act_prev.triggered.connect(self.prev_tab)
        self.addAction(act_prev)
        
        QApplication.instance().installEventFilter(self)