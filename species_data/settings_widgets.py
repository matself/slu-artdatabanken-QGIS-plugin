"""Widgets shared by the tabs for remembered and stored settings.

``remembered`` and ``remember`` keep the values of the last run in the QGIS settings, and
``StoredSettingsRow`` lets the user take the settings from a result layer made earlier, so a
result can be repeated exactly. The JSON is in the layer metadata (see ``settings.py``).
"""
from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication, QSettings
from qgis.PyQt.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from . import settings

_PREFIX = "species_data/"


def tr(text):
    return QCoreApplication.translate("SettingsWidgets", text)


def remembered(name: str, cls):
    """The settings of the last run (class ``cls``), or None."""
    return settings.loads(QSettings().value(_PREFIX + name, ""), cls)


def remember(name: str, params):
    QSettings().setValue(_PREFIX + name, settings.dumps(params))


def remember_value(name: str, value):
    """A single remembered value, for choices that are not part of the settings of a result."""
    QSettings().setValue(_PREFIX + name, value)


def remembered_value(name: str, default):
    return QSettings().value(_PREFIX + name, default)


def stored_in(layer, key: str, cls):
    """The settings stored in the metadata of ``layer`` under ``key``, or None."""
    for text in layer.metadata().keywords().get(key, []):
        params = settings.loads(text, cls)
        if params is not None:
            return params
    return None


class StoredSettingsRow(QWidget):
    """"Use the settings of a result": a list of the layers that carry settings and a button.

    The row is hidden while no layer in the project carries settings of its kind.
    """

    def __init__(self, key: str, cls, apply, parent=None):
        super().__init__(parent)
        self._key, self._cls, self._apply = key, cls, apply
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(tr("Settings of an earlier result:")))
        self.box = QComboBox()
        layout.addWidget(self.box, 1)
        self.button = QPushButton(tr("Use"))
        self.button.clicked.connect(self._use)
        layout.addWidget(self.button)
        project = QgsProject.instance()
        project.layersAdded.connect(self.refresh)
        project.layersRemoved.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        self.box.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and stored_in(layer, self._key, self._cls):
                self.box.addItem(layer.name(), layer.id())
        self.setVisible(self.box.count() > 0)

    def _use(self):
        layer = QgsProject.instance().mapLayer(self.box.currentData())
        params = stored_in(layer, self._key, self._cls) if layer else None
        if params is not None:
            self._apply(params)
