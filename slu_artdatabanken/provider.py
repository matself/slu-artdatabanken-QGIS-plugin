"""Processing provider for SLU Artdatabanken."""
from pathlib import Path

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithms.example_algorithm import ExampleAlgorithm


class SluArtdatabankenProvider(QgsProcessingProvider):
    def id(self):
        return "slu_artdatabanken"

    def name(self):
        return "SLU Artdatabanken"

    def longName(self):  # noqa: N802
        return self.name()

    def icon(self):
        return QIcon(str(Path(__file__).parent / "icon.svg"))

    def loadAlgorithms(self):  # noqa: N802
        self.addAlgorithm(ExampleAlgorithm())
