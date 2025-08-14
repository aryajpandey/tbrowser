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