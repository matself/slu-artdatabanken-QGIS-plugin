"""Dock widget for Species Data (SLU Artdatabanken)."""
from qgis.PyQt.QtWidgets import QDockWidget, QLabel, QVBoxLayout, QWidget


class SpeciesDataDockWidget(QDockWidget):
    """Minimal code-only dock widget (no .ui file, so no uic differences Qt5/Qt6)."""

    def __init__(self, parent=None):
        super().__init__("Species Data (SLU Artdatabanken)", parent)
        self.setObjectName("SpeciesDataDockWidget")

        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.addWidget(QLabel("Species Data (SLU Artdatabanken)"))
        layout.addStretch()
        self.setWidget(content)
