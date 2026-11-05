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


def test_the_classes_are_drawn_in_the_order_of_the_legend():
    from qgis.core import (
        QgsCoordinateReferenceSystem,
        QgsExpression,
        QgsFeature,
        QgsGeometry,
        QgsMapRendererParallelJob,
        QgsMapSettings,
        QgsPointXY,
        QgsRectangle,
        QgsVectorLayer,
    )
    from qgis.PyQt.QtCore import QSize
    from qgis.PyQt.QtGui import QColor

    from species_data.locality_tab import CATEGORY_COLORS, RANK_EXPRESSION, _renderer

    assert not QgsExpression(RANK_EXPRESSION).hasParserError(), QgsExpression(RANK_EXPRESSION).parserErrorString()

    layer = QgsVectorLayer("Point?crs=EPSG:3006&field=category:string&field=n_observations:integer", "t", "memory")
    names = list(CATEGORY_COLORS)
    # Added in the order of the legend, so an expression that did nothing would draw the wrong way round.
    # The number of observations is the opposite of the legend order, so it cannot decide either.
    features = []
    for number, name in enumerate(names):
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(1000, 1000)))
        feature.setAttributes([name, 10 + number * 10])
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    layer.setRenderer(_renderer())

    def drawn_on_top(pair):
        layer.setSubsetString("category IN (" + ",".join(f"'{name}'" for name in pair) + ")")
        settings = QgsMapSettings()
        settings.setLayers([layer])
        settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3006"))
        settings.setExtent(QgsRectangle(900, 900, 1100, 1100))
        settings.setOutputSize(QSize(200, 200))
        settings.setBackgroundColor(QColor("white"))
        job = QgsMapRendererParallelJob(settings)
        job.start()
        job.waitForFinished()
        pixel = job.renderedImage().pixelColor(100, 100)

        def distance(name):
            base = QColor(CATEGORY_COLORS[name])
            mixed = [0.78 * c + 0.22 * 255 for c in (base.red(), base.green(), base.blue())]
            return sum((a - b) ** 2 for a, b in zip(mixed, (pixel.red(), pixel.green(), pixel.blue())))

        return min(pair, key=distance)

    for upper, lower in zip(names, names[1:]):
        assert drawn_on_top([upper, lower]) == upper


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
