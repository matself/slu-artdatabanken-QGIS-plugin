"""The "Localities" tab: group the observations of a fetched layer into localities.

The tab reads a layer made by this plugin (fetched now, or saved to a GeoPackage and opened
again) and writes a new temporary point layer with one point per locality. The grouping
itself is in ``clustering.py``. The layer is read on the main thread and the grouping runs
in a background task, so the window stays usable on large layers.
"""
from datetime import date, datetime

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsGeometry,
    QgsLayerMetadata,
    QgsMarkerSymbol,
    QgsPointXY,
    QgsProject,
    QgsProperty,
    QgsRendererCategory,
    QgsSymbolLayer,
    QgsTask,
    QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtCore import QCoreApplication, QMetaType
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import clustering, provenance, source_check
from .wfs import CRS

CATEGORY_COLORS = {
    clustering.STRONG: "#1a9850",
    clustering.SPORADIC: "#91cf60",
    clustering.HISTORICAL: "#aaaaaa",
    clustering.NOT_REFOUND: "#fdae61",
    clustering.UNCERTAIN: "#2b83ba",
}


def tr_noop(text):
    """Mark a string for translation without translating it yet (see scripts/translations.py)."""
    return text


# Shown in the layer legend and attribute table. Translated where they are displayed.
CATEGORY_LABELS = {
    clustering.STRONG: tr_noop("Strong current locality"),
    clustering.SPORADIC: tr_noop("Sporadic current locality"),
    clustering.HISTORICAL: tr_noop("Historical locality (no recent records)"),
    clustering.NOT_REFOUND: tr_noop("Not refound"),
    clustering.UNCERTAIN: tr_noop("Uncertain"),
}


def tr(text):
    return QCoreApplication.translate("LocalityTab", text)


class ClusterTask(QgsTask):
    """Group the points of every species in the background."""

    def __init__(self, by_species: dict, params: clustering.Params, on_done):
        super().__init__("Species Data: grouping observations into localities", QgsTask.Flag.CanCancel)
        self.by_species = by_species
        self.params = params
        self._on_done = on_done
        self.results = {}

    def run(self):
        total = sum(len(points) for points in self.by_species.values()) or 1
        done = 0
        for species, points in self.by_species.items():
            if self.isCanceled():
                return False
            self.results[species] = clustering.cluster(points, self.params)
            done += len(points)
            self.setProgress(100 * done / total)
        return True

    def finished(self, ok):
        if ok:
            self._on_done(self.results)


class LocalityTab(QWidget):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self._task = None
        self._source = None  # layer being grouped
        self._points = {}

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.layer_box = QgsMapLayerComboBox()
        self.layer_box.setFilters(Qgis.LayerFilter.PointLayer)
        self.layer_box.setAllowEmptyLayer(True)
        form.addRow(tr("Observation layer"), self.layer_box)

        self.link_distance = self._spin(0, 5000, 100)
        form.addRow(tr("Link distance between exact points (m)"), self.link_distance)
        self.use_uncertainty = QCheckBox(tr("Add the coordinate uncertainty to the link distance"))
        self.use_uncertainty.setChecked(True)
        form.addRow(self.use_uncertainty)
        self.max_uncertainty = self._spin(1, 100000, 500)
        form.addRow(tr("Leave out observations less precise than (m)"), self.max_uncertainty)
        self.bridge_uncertainty = self._spin(0, 100000, 100)
        self.bridge_uncertainty.setToolTip(
            tr(
                "Observations less precise than this join the nearest locality, but never "
                "join two localities together."
            )
        )
        form.addRow(tr("Vague observations only join one locality above (m)"), self.bridge_uncertainty)
        self.max_radius = self._spin(0, 100000, int(clustering.Params().max_radius))
        self.max_radius.setToolTip(
            tr(
                "A string of observations, for example along a shore, is split up when it is "
                "wider than this. 0 means no limit."
            )
        )
        form.addRow(tr("Largest locality radius (m, 0 = no limit)"), self.max_radius)
        self.recent_years = self._spin(0, 100, 5)
        form.addRow(tr("Current: last record at most this many years ago"), self.recent_years)
        self.historical_years = self._spin(1, 200, 15)
        form.addRow(tr("Historical: last record more than this many years ago"), self.historical_years)
        self.strong_years = self._spin(1, 100, 5)
        form.addRow(tr("Strong: years with records needed"), self.strong_years)
        layout.addLayout(form)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.run_button = QPushButton(tr("Group into localities"))
        self.run_button.clicked.connect(self._start)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        layout.addWidget(self.run_button)
        layout.addStretch()

        self.layer_box.layerChanged.connect(self._layer_changed)
        self._layer_changed(self.layer_box.currentLayer())

    @staticmethod
    def _spin(low, high, value):
        box = QSpinBox()
        box.setRange(low, high)
        box.setValue(value)
        return box

    # -- checking the chosen layer -------------------------------------------------------

    @staticmethod
    def check(layer) -> list:
        """Problems that make ``layer`` unusable, translated for the user."""
        if layer is None:
            return [tr("Choose a layer fetched with this plugin.")]
        abstract = layer.metadata().abstract() or ""
        if not abstract and hasattr(layer, "loadDefaultMetadata"):
            layer.loadDefaultMetadata()  # a GeoPackage keeps the metadata inside the file
            abstract = layer.metadata().abstract() or ""
        is_point = _is_point(layer)
        found = source_check.problems(
            [f.name() for f in layer.fields()], abstract, is_point, layer.featureCount()
        )
        return [_describe(code, detail) for code, detail in found]

    def _layer_changed(self, layer):
        found = self.check(layer)
        self.run_button.setEnabled(not found and self._task is None)
        self.status.setText("\n".join(found))

    # -- running -------------------------------------------------------------------------

    def _read_points(self, layer) -> dict:
        """Points per species, in SWEREF 99 TM so distances are metres."""
        target = QgsCoordinateReferenceSystem(CRS)
        transform = QgsCoordinateTransform(layer.crs(), target, QgsProject.instance())
        names = layer.fields().names()
        has_flag = "isNotRediscoveredObservation" in names
        has_present = "isPresentObservation" in names
        by_species = {}
        for feature in layer.getFeatures():
            geometry = feature.geometry()
            if geometry.isNull():
                continue
            not_refound = bool(has_flag and feature["isNotRediscoveredObservation"] is True)
            if has_present and feature["isPresentObservation"] is False and not not_refound:
                continue  # an observation of absence says nothing about where it grows
            point = transform.transform(geometry.asPoint())
            end = feature["endDate"]
            year = end.year() if hasattr(end, "year") and end.isValid() else None
            uncertainty = feature["coordinateUncertaintyInMeters"]
            uncertainty = uncertainty if isinstance(uncertainty, (int, float)) else None
            species = feature["scientificName"] or tr("(no name)")
            by_species.setdefault(species, []).append(
                clustering.Point(point.x(), point.y(), year, uncertainty, not_refound)
            )
        return by_species

    def _params(self) -> clustering.Params:
        return clustering.Params(
            link_distance=self.link_distance.value(),
            uncertainty_weight=1.0 if self.use_uncertainty.isChecked() else 0.0,
            max_uncertainty=self.max_uncertainty.value(),
            bridge_uncertainty=self.bridge_uncertainty.value(),
            max_radius=self.max_radius.value(),
            reference_year=date.today().year,
            recent_years=self.recent_years.value(),
            historical_years=self.historical_years.value(),
            strong_min_years=self.strong_years.value(),
        )

    def _start(self):
        layer = self.layer_box.currentLayer()
        if self.check(layer):
            return
        self._source = layer
        self._points = self._read_points(layer)
        params = self._params()
        if not any(self._points.values()):
            QMessageBox.information(self, tr("Species Data"), tr("The layer has no usable observations."))
            return
        self.run_button.setEnabled(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.status.setText(tr("Grouping observations into localities..."))
        self._params_used = params
        self._task = ClusterTask(self._points, params, self._done)
        self._task.progressChanged.connect(lambda value: self.progress.setValue(int(value)))
        self._task.taskTerminated.connect(self._finished)
        QgsApplication.taskManager().addTask(self._task)

    def _finished(self):
        self._task = None
        self.progress.setVisible(False)
        self._layer_changed(self.layer_box.currentLayer())

    def _done(self, results):
        params = self._params_used
        layer = build_layer(results, self._source, params)
        self._finished()
        QgsProject.instance().addMapLayer(layer)
        left_out = sum(len(r.left_out) for r in results.values())
        message = tr("{n} localities from {m} observations.").format(
            n=layer.featureCount(), m=sum(len(p) for p in self._points.values())
        )
        if left_out:
            message += " " + tr("{n} observations were less precise than the limit and left out.").format(n=left_out)
        self.status.setText(message)
        self.iface.messageBar().pushMessage(tr("Species Data"), provenance.citation(datetime.now()), duration=8)


def _describe(code, detail) -> str:
    if code == source_check.NOT_POINT:
        return tr("The layer does not have point geometry.")
    if code == source_check.MISSING_FIELDS:
        return tr("Missing fields: {fields}.").format(fields=detail)
    if code == source_check.NO_SOURCE:
        return tr(
            "The layer metadata does not name the data source of this plugin. "
            "Save the layer together with its metadata, or fetch the data again."
        )
    return tr("The layer has no observations.")


def _is_point(layer) -> bool:
    return layer.geometryType() == Qgis.GeometryType.Point


def build_layer(results: dict, source, params: clustering.Params):
    """A temporary layer with one point per locality."""
    layer = QgsVectorLayer(f"Point?crs={CRS}", f"{source.name()}: localities", "memory")
    fields = (
        ("species", QMetaType.Type.QString),
        ("locality_id", QMetaType.Type.Int),
        ("category", QMetaType.Type.QString),
        ("n_observations", QMetaType.Type.Int),
        ("n_years", QMetaType.Type.Int),
        ("first_year", QMetaType.Type.Int),
        ("last_year", QMetaType.Type.Int),
        ("radius_m", QMetaType.Type.Int),
        ("n_not_refound", QMetaType.Type.Int),
    )
    layer.dataProvider().addAttributes([QgsField(name, kind) for name, kind in fields])
    layer.updateFields()
    features = []
    for species, result in sorted(results.items()):
        for loc in result.localities:
            feature = QgsFeature(layer.fields())
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(loc.x, loc.y)))
            feature.setAttributes(
                [species, loc.id, loc.category, loc.count, len(loc.years), loc.first_year,
                 loc.last_year, round(loc.radius), loc.not_refound_count]
            )
            features.append(feature)
    layer.dataProvider().addFeatures(features)
    layer.setRenderer(_renderer())
    layer.setMetadata(_metadata(layer.name(), source, params))
    return layer


# Diameter in millimetres, growing with the logarithm of the number of observations from
# SIZE_MIN (one observation) to SIZE_MAX (SIZE_FULL observations or more), so that a locality
# with a handful of records still looks clearly bigger than one with a single record.
SIZE_MIN = 2.5
SIZE_MAX = 10.0
SIZE_FULL = 30
SIZE_EXPRESSION = (
    f'{SIZE_MIN} + {SIZE_MAX - SIZE_MIN} * min(1, ln("n_observations") / ln({SIZE_FULL}))'
)
FILL_ALPHA = 200  # about 80 %, so the colours still show on a grey base map


def _renderer():
    categories = []
    for category, color in CATEGORY_COLORS.items():
        base = QColor(color)
        fill = QColor(base)
        fill.setAlpha(FILL_ALPHA)
        outline = base.darker(170)
        symbol = QgsMarkerSymbol.createSimple(
            {
                "name": "circle",
                "color": f"{fill.red()},{fill.green()},{fill.blue()},{fill.alpha()}",
                "size": str(SIZE_MIN),
                "outline_color": outline.name(),
                "outline_width": "0.4",
            }
        )
        # On the symbol layer: the symbol-level data defined size is not applied here.
        symbol.symbolLayer(0).setDataDefinedProperty(
            QgsSymbolLayer.Property.Size, QgsProperty.fromExpression(SIZE_EXPRESSION)
        )
        categories.append(QgsRendererCategory(category, symbol, tr(CATEGORY_LABELS[category])))
    renderer = QgsCategorizedSymbolRenderer("category", categories)
    # Large localities are drawn first so small ones stay visible on top of them.
    order = QgsFeatureRequest.OrderBy([QgsFeatureRequest.OrderByClause('"n_observations"', False)])
    renderer.setOrderBy(order)
    renderer.setOrderByEnabled(True)
    return renderer


def _metadata(name, source, params):
    meta = QgsLayerMetadata()
    meta.setTitle(name)
    lines = [
        source.metadata().abstract() or provenance.SOURCE,
        "",
        f"Observations grouped into localities with the plugin Species Data (SLU Artdatabanken): "
        f"link distance {params.link_distance:g} m, "
        f"{'with' if params.uncertainty_weight else 'without'} coordinate uncertainty, "
        f"observations less precise than {params.max_uncertainty:g} m left out, "
        f"vague observations (over {params.bridge_uncertainty:g} m) join one locality only, "
        f"localities wider than a radius of {params.max_radius:g} m split up (0 = no limit).",
        provenance.DISCLAIMER,
    ]
    meta.setAbstract("\n".join(lines))
    meta.setRights(source.metadata().rights() or [provenance.DISCLAIMER])
    meta.setType("dataset")
    meta.setCrs(QgsCoordinateReferenceSystem(CRS))
    return meta
