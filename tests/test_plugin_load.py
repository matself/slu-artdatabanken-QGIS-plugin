"""Load the plugin inside a real QGIS (skipped when QGIS is not importable)."""
import sys
from pathlib import Path

import pytest

pytest.importorskip("qgis.core")

from qgis.testing import start_app  # noqa: E402
from qgis.testing.mocked import get_iface  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

start_app()


def test_class_factory_and_lifecycle():
    from species_data import classFactory

    plugin = classFactory(get_iface())
    plugin.initGui()
    plugin.unload()


def test_the_first_click_shows_the_panel_and_the_second_hides_it():
    from qgis.gui import QgsMapCanvas
    from qgis.PyQt.QtWidgets import QMainWindow

    from species_data import classFactory

    window = QMainWindow()
    canvas = QgsMapCanvas()

    class Iface:
        def mainWindow(self):
            return window

        def mapCanvas(self):
            return canvas

        def addDockWidget(self, area, dock):
            window.addDockWidget(area, dock)

        def removeDockWidget(self, dock):
            window.removeDockWidget(dock)

    plugin = classFactory(Iface())
    window.show()
    plugin.run()
    assert plugin.dock.isVisible()
    plugin.run()
    assert not plugin.dock.isVisible()
    plugin.run()
    assert plugin.dock.isVisible()
