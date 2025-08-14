USING_QT6 = False
try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QFrame, QLineEdit, QVBoxLayout, QSizePolicy
    USING_QT6 = True
except Exception:
    from PyQt5.QtCore import Qt  # type: ignore
    from PyQt5.QtWidgets import QFrame, QLineEdit, QVBoxLayout, QSizePolicy  # type: ignore

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

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding if USING_QT6 else QSizePolicy.Expanding,
            QSizePolicy.Policy.Fixed if USING_QT6 else QSizePolicy.Fixed
        )

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
            pw = self.parent().width() if self.parent() else 800
            ph = self.parent().height() if self.parent() else 600
            w = int(pw * 0.7)
            h = 56
            x = int((pw - w) / 2)
            y = ph - h - 70
            self.setGeometry(x, y, w, h)
            self.show()
            self.input.setFocus()
            self.input.setText("/")  # Always start with "/"

    def keyPressEvent(self, event):
        esc = (Qt.Key.Key_Escape if USING_QT6 else Qt.Key_Escape)
        if event.key() == esc:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)
