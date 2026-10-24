"""Dock widget for Species Data (SLU Artdatabanken).

Code-only (no .ui file, so no uic differences between Qt5 and Qt6). The five
tabs follow the structure of SLU Artdatabanken's own search page, Fynddata.
"""
from datetime import date, datetime

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
)
from qgis.PyQt.QtCore import QCoreApplication, QDate, Qt
from qgis.PyQt.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import counting, layers, provenance
from .net import NetworkError, feature_probe
from .query import (
    ABSENT,
    BOTH,
    PRESENT,
    REDLIST_CATEGORIES,
    THREATENED_CATEGORIES,
    WARN_THRESHOLD,
    BoundingBoxWgs84,
    Query,
    assess_count,
)

COUNTIES = (
    "Blekinge", "Dalarna", "Gotland", "Gävleborg", "Halland", "Jämtland", "Jönköping",
    "Kalmar", "Kronoberg", "Norrbotten", "Skåne", "Stockholm", "Södermanland", "Uppsala",
    "Värmland", "Västerbotten", "Västernorrland", "Västmanland", "Västra Götaland",
    "Örebro", "Östergötland",
)  # fmt: skip

# Data providers known to appear in the open WFS. The full list needs the REST API.
DATASETS = ((1, "Artportalen"), (19, "iNaturalist"))

TERMS_URL = "https://www.slu.se/artdatabanken/rapportering-och-fynd/oppna-data-och-apier/api-villkor/"


def tr(text):
    return QCoreApplication.translate("SpeciesDataDockWidget", text)


class SpeciesDataDockWidget(QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__(tr("Species Data (SLU Artdatabanken)"), parent)
        self.iface = iface
        self.setObjectName("SpeciesDataDockWidget")
        self._count = None  # (Query, Count) of the last count

        content = QWidget(self)
        layout = QVBoxLayout(content)
        tabs = QTabWidget()
        tabs.addTab(self._taxa_tab(), tr("Taxa"))
        tabs.addTab(self._time_tab(), tr("Time"))
        tabs.addTab(self._geography_tab(), tr("Geography"))
        tabs.addTab(self._properties_tab(), tr("Properties"))
        tabs.addTab(self._datasets_tab(), tr("Datasets"))
        layout.addWidget(tabs)

        self.count_button = QPushButton(tr("Count observations"))
        self.count_button.clicked.connect(self.on_count)
        self.count_label = QLabel("")
        self.count_label.setWordWrap(True)
        self.create_button = QPushButton(tr("Create layer"))
        self.create_button.clicked.connect(self.on_create)
        layout.addWidget(self.count_button)
        layout.addWidget(self.count_label)
        layout.addWidget(self.create_button)

        source = QLabel(
            tr(
                "Data: SLU Artdatabanken, Species Observation System. "
                "Independent plugin, not owned or endorsed by SLU. "
                '<a href="{url}">Terms of use</a>.'
            ).format(url=TERMS_URL)
        )
        source.setWordWrap(True)
        source.setOpenExternalLinks(True)
        layout.addWidget(source)
        layout.addStretch()
        self.setWidget(content)

    # -- tabs --------------------------------------------------------------

    def _taxa_tab(self):
        tab = QWidget()
        form = QVBoxLayout(tab)
        self.vascular_only = QCheckBox(tr("Vascular plants only"))
        self.vascular_only.setChecked(True)
        self.names = QPlainTextEdit()
        self.names.setPlaceholderText(
            tr("One species name per line, scientific or Swedish\n(for example: vitsippa)")
        )
        form.addWidget(self.vascular_only)
        form.addWidget(QLabel(tr("Species names (leave empty for all species)")))
        form.addWidget(self.names)
        return tab

    def _time_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        year = date.today().year
        self.period = QComboBox()
        self.period.addItem(tr("All years"), "all")
        self.period.addItem(tr("Current year"), "current")
        self.period.addItem(tr("Previous year"), "previous")
        self.period.addItem(tr("Last 5 years"), "5")
        self.period.addItem(tr("Last 25 years"), "25")
        self.period.addItem(tr("Custom"), "custom")
        self.date_from = QDateEdit(QDate(year, 1, 1))
        self.date_to = QDateEdit(QDate(year, 12, 31))
        for edit in (self.date_from, self.date_to):
            edit.setCalendarPopup(True)
            edit.setEnabled(False)
        self.period.currentIndexChanged.connect(
            lambda: [
                e.setEnabled(self.period.currentData() == "custom")
                for e in (self.date_from, self.date_to)
            ]
        )
        form.addRow(tr("Period"), self.period)
        form.addRow(tr("From"), self.date_from)
        form.addRow(tr("To"), self.date_to)
        return tab

    def _geography_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.area_canvas = QRadioButton(tr("Current map extent"))
        self.area_county = QRadioButton(tr("County"))
        self.area_sweden = QRadioButton(tr("Whole of Sweden"))
        self.area_canvas.setChecked(True)
        self.county = QComboBox()
        self.county.addItems(COUNTIES)
        self.county.setCurrentText("Skåne")
        self.county.setEnabled(False)
        self.area_county.toggled.connect(self.county.setEnabled)
        layout.addWidget(self.area_canvas)
        layout.addWidget(self.area_county)
        layout.addWidget(self.county)
        layout.addWidget(self.area_sweden)
        layout.addStretch()
        return tab

    def _properties_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()
        self.occurrence = QComboBox()
        self.occurrence.addItem(tr("Only observed"), PRESENT)
        self.occurrence.addItem(tr("Only not found"), ABSENT)
        self.occurrence.addItem(tr("Observed and not found"), BOTH)
        self.max_uncertainty = QSpinBox()
        self.max_uncertainty.setRange(0, 100000)
        self.max_uncertainty.setSpecialValueText(tr("No limit"))
        self.max_uncertainty.setSuffix(" m")
        form.addRow(tr("Occurrence"), self.occurrence)
        form.addRow(tr("Max coordinate uncertainty"), self.max_uncertainty)
        layout.addLayout(form)
        self.include_uncertain = QCheckBox(tr("Include uncertain identifications"))
        self.verified_only = QCheckBox(tr("Verified observations only"))
        layout.addWidget(self.include_uncertain)
        layout.addWidget(self.verified_only)

        box = QGroupBox(tr("Red list categories (none selected: all)"))
        box_layout = QVBoxLayout(box)
        self.redlist = {}
        for code in REDLIST_CATEGORIES:
            check = QCheckBox(code)
            self.redlist[code] = check
            box_layout.addWidget(check)
        threatened = QPushButton(tr("CR, EN, VU, NT"))
        threatened.clicked.connect(self._select_threatened)
        box_layout.addWidget(threatened)
        layout.addWidget(box)
        layout.addStretch()
        return tab

    def _select_threatened(self):
        for code, box in self.redlist.items():
            box.setChecked(code in THREATENED_CATEGORIES)

    def _datasets_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel(tr("None selected: all datasets")))
        self.datasets = {}
        for provider_id, name in DATASETS:
            check = QCheckBox(name)
            self.datasets[provider_id] = check
            layout.addWidget(check)
        layout.addStretch()
        return tab

    # -- query -------------------------------------------------------------

    def build_query(self) -> Query:
        names = tuple(
            line.strip() for line in self.names.toPlainText().splitlines() if line.strip()
        )
        date_from, date_to = self._period()
        bbox = self._canvas_bbox() if self.area_canvas.isChecked() else None
        return Query(
            organism_group="Kärlväxter" if self.vascular_only.isChecked() else None,
            names=names,
            county=self.county.currentText() if self.area_county.isChecked() else None,
            bbox_wgs84=bbox,
            date_from=date_from,
            date_to=date_to,
            occurrence=self.occurrence.currentData(),
            verified_only=self.verified_only.isChecked(),
            exclude_uncertain_identification=not self.include_uncertain.isChecked(),
            max_uncertainty_m=self.max_uncertainty.value() or None,
            redlist_categories=tuple(c for c, box in self.redlist.items() if box.isChecked()),
            dataset_ids=tuple(i for i, box in self.datasets.items() if box.isChecked()),
        )

    def _period(self):
        year = date.today().year
        choice = self.period.currentData()
        if choice == "current":
            return date(year, 1, 1), date(year, 12, 31)
        if choice == "previous":
            return date(year - 1, 1, 1), date(year - 1, 12, 31)
        if choice in ("5", "25"):
            return date(year - int(choice) + 1, 1, 1), date(year, 12, 31)
        if choice == "custom":
            return self.date_from.date().toPyDate(), self.date_to.date().toPyDate()
        return None, None

    def _canvas_bbox(self):
        canvas = self.iface.mapCanvas()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(
            canvas.mapSettings().destinationCrs(), wgs84, QgsProject.instance()
        )
        extent = transform.transformBoundingBox(canvas.extent())
        return BoundingBoxWgs84(
            extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()
        )

    # -- actions -----------------------------------------------------------

    def _run_count(self, query):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            return counting.count(feature_probe(query))
        except NetworkError as exc:
            QMessageBox.warning(self, tr("Species Data"), str(exc))
            return None
        finally:
            QApplication.restoreOverrideCursor()

    def _show_count(self, result):
        assessment = assess_count(result.value)
        number = f"{result.value:,}".replace(",", " ")
        if assessment.at_least:
            text = tr("At least {n} observations: too many. Narrow the search.").format(n=number)
        elif assessment.status == "warn":
            text = tr(
                "About {n} observations. That is a lot for a dot map "
                "(warning from {w})."
            ).format(n=number, w=WARN_THRESHOLD)
        else:
            text = tr("About {n} observations.").format(n=number)
        self.count_label.setText(text)
        return assessment

    def on_count(self):
        query = self.build_query()
        result = self._run_count(query)
        if result is not None:
            self._count = (query, result)
            self._show_count(result)

    def on_create(self):
        query = self.build_query()
        if self._count is None or self._count[0] != query:
            result = self._run_count(query)
            if result is None:
                return
            self._count = (query, result)
        result = self._count[1]
        assessment = self._show_count(result)
        if assessment.at_least:
            QMessageBox.warning(
                self,
                tr("Species Data"),
                tr("The search matches too many observations. Narrow it down."),
            )
            return
        if assessment.status == "warn":
            answer = QMessageBox.question(
                self,
                tr("Species Data"),
                tr("The layer will load about {n} observations. Continue?").format(n=result.value),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        name = self._layer_name(query, result)
        layer = layers.create_layer(query, name, result)
        if layer is None:
            QMessageBox.warning(self, tr("Species Data"), tr("The layer could not be opened."))
            return
        QgsProject.instance().addMapLayer(layer)
        self.iface.messageBar().pushMessage(
            tr("Species Data"), provenance.citation(datetime.now()), duration=8
        )

    @staticmethod
    def _layer_name(query, result):
        what = ", ".join(query.names) if query.names else (query.organism_group or tr("Species"))
        return f"{what} ({result.value})"

