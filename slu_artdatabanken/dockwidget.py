"""Dock widget for SLU Artdatabanken."""
from qgis.PyQt.QtWidgets import QDockWidget, QLabel, QVBoxLayout, QWidget


class SluArtdatabankenDockWidget(QDockWidget):
    """Minimal code-only dock widget (no .ui file, so no uic differences Qt5/Qt6)."""

    def __init__(self, parent=None):
        super().__init__("SLU Artdatabanken", parent)
        self.setObjectName("SluArtdatabankenDockWidget")

        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.addWidget(QLabel("Hello from SLU Artdatabanken!"))
        layout.addStretch()
        self.setWidget(content)
