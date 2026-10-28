"""The "Co-occurrence" tab: find places where several species occur together.

It reads a locality layer made by the "Localities" tab (one locality per species) and writes a
new temporary point layer with one point per place. The grouping is in ``cooccurrence.py``.
"""
import re
from datetime import datetime

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsGradientColorRamp,
    QgsGradientStop,
    QgsHeatmapRenderer,
    QgsField,
    QgsGeometry,
    QgsLayerMetadata,
    QgsMarkerSymbol,
    QgsPointXY,
    QgsProject,
    QgsRuleBasedRenderer,
    QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtCore import QCoreApplication, QMetaType, Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import cooccurrence, provenance
from .wfs import CRS

# What a locality layer from the Localities tab must have.
REQUIRED_FIELDS = (
    "species",
    "locality_id",
    "category",
    "n_observations",
    "n_not_refound",
    "radius_m",
    "first_year",
    "last_year",
)
# One colour per number of species, light to dark, so more species is always darker.
RICHNESS_COLORS = {2: "#6baed6", 3: "#2171b5", 4: "#08306b"}
ALL_SPECIES_COLOR = "#e31a1c"
SINGLE_COLOR = "#9e9e9e"
POINTS, HEAT = "points", "heat"
HEAT_RADIUS_MM = 10
# Places with one species weigh nothing, several species weigh n - 1, and every chosen species
# together weighs one more, so only co-occurrence lights up the map.
HEAT_WEIGHT = '"n_species" - 1 + if("all_species", 1, 0)'


def tr(text):
    return QCoreApplication.translate("CooccurrenceTab", text)


def column_name(species: str) -> str:
    """A field name for a species, for example ``n_primula_farinosa``."""
    return "n_" + re.sub(r"[^a-z0-9]+", "_", species.lower()).strip("_")[:40]


class CooccurrenceTab(QWidget):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.layer_box = QgsMapLayerComboBox()
        self.layer_box.setFilters(Qgis.LayerFilter.PointLayer)
        self.layer_box.setAllowEmptyLayer(True)
        form.addRow(tr("Locality layer"), self.layer_box)
        layout.addLayout(form)

        layout.addWidget(QLabel(tr("Species to look for together:")))
        self.species_list = QListWidget()
        self.species_list.setMaximumHeight(120)
        layout.addWidget(self.species_list)

        params = QFormLayout()
        self.max_gap = self._spin(0, 5000, int(cooccurrence.Params().max_gap))
        self.max_gap.setToolTip(
            tr("Localities of different species belong to the same place when their centres are "
               "at most this far apart, plus the radii of the two localities.")
        )
        params.addRow(tr("Largest gap between localities (m)"), self.max_gap)
        self.max_radius = self._spin(0, 100000, int(cooccurrence.Params().max_radius))
        self.max_radius.setToolTip(tr("A place wider than this is split up. 0 means no limit."))
        params.addRow(tr("Largest place radius (m, 0 = no limit)"), self.max_radius)
        layout.addLayout(params)
        look = QFormLayout()
        self.style_box = QComboBox()
        self.style_box.addItem(tr("Points"), POINTS)
        self.style_box.addItem(tr("Heat map"), HEAT)
        look.addRow(tr("Show as"), self.style_box)
        self.heat_radius = self._spin(1, 100, HEAT_RADIUS_MM)
        self.heat_radius.setToolTip(
            tr("Radius of the heat in millimetres on the screen. Places with all species weigh most, "
               "places with one species do not count.")
        )
        look.addRow(tr("Heat map radius (mm)"), self.heat_radius)
        self.style_box.currentIndexChanged.connect(
            lambda: self.heat_radius.setEnabled(self.style_box.currentData() == HEAT)
        )
        self.heat_radius.setEnabled(False)
        layout.addLayout(look)
        self.only_current = QCheckBox(tr("Only current localities (recent records)"))
        self.count_not_refound = QCheckBox(tr('Count "searched for, not found" as present'))
        layout.addWidget(self.only_current)
        layout.addWidget(self.count_not_refound)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.run_button = QPushButton(tr("Find places with several species"))
        self.run_button.clicked.connect(self._run)
        layout.addWidget(self.status)
        layout.addWidget(self.run_button)
        layout.addStretch()

        self.layer_box.layerChanged.connect(self._layer_changed)
        self.species_list.itemChanged.connect(lambda *_: self._refresh())
        self._layer_changed(self.layer_box.currentLayer())

    @staticmethod
    def _spin(low, high, value):
        box = QSpinBox()
        box.setRange(low, high)
        box.setValue(value)
        return box

    # -- the chosen layer ----------------------------------------------------------------

    @staticmethod
    def problem(layer) -> str:
        """Why ``layer`` cannot be used, or an empty string."""
        if layer is None:
            return tr("Choose the locality layer made on the Localities tab.")
        names = layer.fields().names()
        missing = [n for n in REQUIRED_FIELDS if n not in names]
        if missing:
            return tr("This is not a locality layer from the Localities tab. Missing fields: {fields}.").format(
                fields=", ".join(missing)
            )
        if layer.featureCount() == 0:
            return tr("The layer has no localities.")
        return ""

    @staticmethod
    def species_in(layer) -> list:
        return sorted({v for v in layer.uniqueValues(layer.fields().indexOf("species")) if v})

    def _layer_changed(self, layer):
        self.species_list.blockSignals(True)
        self.species_list.clear()
        if not self.problem(layer):
            for name in self.species_in(layer):
                item = QListWidgetItem(name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.species_list.addItem(item)
        self.species_list.blockSignals(False)
        self._refresh()

    def _chosen(self) -> tuple:
        return tuple(
            self.species_list.item(i).text()
            for i in range(self.species_list.count())
            if self.species_list.item(i).checkState() == Qt.CheckState.Checked
        )

    def _refresh(self):
        layer = self.layer_box.currentLayer()
        problem = self.problem(layer)
        chosen = self._chosen()
        if not problem and len(chosen) < 2:
            problem = tr("Co-occurrence needs at least two species. Tick two or more in the list.")
        self.status.setText(problem)
        self.run_button.setEnabled(not problem)

    # -- running -------------------------------------------------------------------------

    def _nodes(self, layer) -> list:
        transform = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem(CRS), QgsProject.instance())
        nodes = []
        for f in layer.getFeatures():
            if f.geometry().isNull() or not f["species"]:
                continue
            p = transform.transform(f.geometry().asPoint())
            nodes.append(
                cooccurrence.Node(
                    species=f["species"], x=p.x(), y=p.y(), radius=float(f["radius_m"] or 0),
                    observations=int(f["n_observations"] or 0), not_refound=int(f["n_not_refound"] or 0),
                    category=f["category"] or "", first_year=_year(f["first_year"]),
                    last_year=_year(f["last_year"]),
                )
            )
        return nodes

    def _params(self) -> cooccurrence.Params:
        return cooccurrence.Params(
            max_gap=self.max_gap.value(),
            max_radius=self.max_radius.value(),
            only_current=self.only_current.isChecked(),
            count_not_refound=self.count_not_refound.isChecked(),
        )

    def _run(self):
        layer = self.layer_box.currentLayer()
        if self.problem(layer):
            return
        wanted = self._chosen()
        params = self._params()
        result = cooccurrence.find_places(self._nodes(layer), wanted, params)
        if not result.places:
            QMessageBox.information(self, tr("Species Data"), tr("No places found."))
            return
        out = build_layer(result, layer, params, self.style_box.currentData(), self.heat_radius.value())
        QgsProject.instance().addMapLayer(out)
        together = sum(1 for p in result.places if p.all_species)
        self.status.setText(
            tr("{n} places, {m} with all {k} species.").format(n=len(result.places), m=together, k=len(wanted))
        )
        self.iface.messageBar().pushMessage(tr("Species Data"), provenance.citation(datetime.now()), duration=8)


def _year(value):
    return int(value) if isinstance(value, (int, float)) else None


def build_layer(result, source, params, style=None, heat_radius_mm=None):
    """A temporary layer with one point per place."""
    layer = QgsVectorLayer(f"Point?crs={CRS}", f"{source.name()}: co-occurrence", "memory")
    species_columns = [column_name(s) for s in result.wanted]
    fields = [
        ("place_id", QMetaType.Type.Int),
        ("species", QMetaType.Type.QString),
        ("n_species", QMetaType.Type.Int),
        ("all_species", QMetaType.Type.Bool),
        ("n_localities", QMetaType.Type.Int),
        ("first_year", QMetaType.Type.Int),
        ("last_year", QMetaType.Type.Int),
        ("radius_m", QMetaType.Type.Int),
        *[(name, QMetaType.Type.Int) for name in species_columns],
    ]
    layer.dataProvider().addAttributes([QgsField(n, k) for n, k in fields])
    layer.updateFields()
    features = []
    for place in result.places:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(place.x, place.y)))
        feature.setAttributes(
            [place.id, "; ".join(place.species), len(place.species), place.all_species,
             sum(place.localities.values()), place.first_year, place.last_year, round(place.radius),
             *[place.localities.get(s) for s in result.wanted]]
        )
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    if style == HEAT:
        layer.setRenderer(_heat_renderer(heat_radius_mm or HEAT_RADIUS_MM))
    else:
        layer.setRenderer(_renderer(len(result.wanted)))
    layer.setMetadata(_metadata(layer.name(), source, params, result))
    return layer


def _symbol(color, size, outline="#ffffff", opacity=255):
    fill = QColor(color)
    fill.setAlpha(opacity)
    return QgsMarkerSymbol.createSimple(
        {"name": "circle", "color": f"{fill.red()},{fill.green()},{fill.blue()},{fill.alpha()}",
         "size": str(size), "outline_color": outline, "outline_width": "0.4"}
    )


def _heat_renderer(radius_mm):
    """A heat map of co-occurrence, from transparent through yellow and orange to dark red."""
    renderer = QgsHeatmapRenderer()
    renderer.setWeightExpression(HEAT_WEIGHT)
    renderer.setRadius(radius_mm)
    renderer.setRadiusUnit(Qgis.RenderUnit.Millimeters)
    renderer.setColorRamp(
        QgsGradientColorRamp(
            QColor(255, 255, 204, 0),
            QColor(128, 0, 38),
            False,
            [
                QgsGradientStop(0.25, QColor(254, 217, 118)),
                QgsGradientStop(0.5, QColor(253, 141, 60)),
                QgsGradientStop(0.75, QColor(227, 26, 28)),
            ],
        )
    )
    return renderer


def _renderer(n_species):
    """Places with every chosen species stand out in red, places with several in blue (darker
    with more species), and places with a single species are small and grey, since there are
    far more of them and they say nothing about co-occurrence. Rules, so each can be switched
    off in the legend. More species are drawn on top."""
    rule = QgsRuleBasedRenderer.Rule
    root = rule(None)
    root.appendChild(
        rule(_symbol(ALL_SPECIES_COLOR, 7, "#7f0000"), 0, 0, '"all_species"',
             tr("All {k} species").format(k=n_species))
    )
    for n in range(n_species - 1, 1, -1):
        color = RICHNESS_COLORS[min(n, max(RICHNESS_COLORS))]
        root.appendChild(
            rule(_symbol(color, 3.5 + n), 0, 0, f'"n_species" = {n} and not "all_species"',
                 tr("{n} species").format(n=n))
        )
    root.appendChild(rule(_symbol(SINGLE_COLOR, 2.5, "#ffffff", 160), 0, 0, "ELSE", tr("1 species")))
    renderer = QgsRuleBasedRenderer(root)
    order = QgsFeatureRequest.OrderBy([QgsFeatureRequest.OrderByClause('"n_species"', True)])
    renderer.setOrderBy(order)
    renderer.setOrderByEnabled(True)
    return renderer


def _metadata(name, source, params, result):
    meta = QgsLayerMetadata()
    meta.setTitle(name)
    meta.setAbstract(
        "\n".join(
            [
                source.metadata().abstract() or provenance.SOURCE,
                "",
                "Places where the species occur together, found with the plugin Species Data "
                f"(SLU Artdatabanken): species {', '.join(result.wanted)}; localities within "
                f"{params.max_gap:g} m plus their radii form one place; places wider than a radius of "
                f"{params.max_radius:g} m are split (0 = no limit); "
                f"{'only current localities; ' if params.only_current else ''}"
                f"{'searched-for-not-found counted as present.' if params.count_not_refound else 'searched-for-not-found not counted.'}",
                provenance.DISCLAIMER,
            ]
        )
    )
    meta.setRights(source.metadata().rights() or [provenance.DISCLAIMER])
    meta.setType("dataset")
    meta.setCrs(QgsCoordinateReferenceSystem(CRS))
    return meta
