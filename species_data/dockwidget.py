"""Dock widget for Species Data (SLU Artdatabanken).

Code-only (no .ui file, so no uic differences between Qt5 and Qt6). The five
sections follow the structure of SLU Artdatabanken's own search page, Fynddata,
and share one scrolling window above the fixed count and create buttons.
"""
from datetime import date, datetime

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
)
from qgis.gui import QgsCollapsibleGroupBox
from qgis.PyQt.QtCore import QCoreApplication, QDate
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDockWidget,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import layers, provenance, snapshot
from .download import CountTask, SnapshotTask
from .query import (
    ABSENT,
    BOTH,
    DEFAULT_ORGANISM_GROUP,
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

# Searches are limited to Artportalen (data provider id 1). Other data providers need the
# REST API to list them, and the choice is kept out of the panel for now.
ARTPORTALEN = 1


def tr_noop(text):
    """Mark a string for translation without translating it yet (see scripts/translations.py)."""
    return text


EXTRA_FIELD_LABELS = (
    ("habitat", tr_noop("Habitat")),
    ("life_stage", tr_noop("Life stage")),
    ("quantity", tr_noop("Quantity")),
    ("project", tr_noop("Project")),
    ("taxon_id", tr_noop("Taxon id (Dyntaxa)")),
    ("modified", tr_noop("Last modified")),
    ("remarks", tr_noop("Remarks (free text, may contain personal data)")),
)

TERMS_URL = "https://www.slu.se/artdatabanken/rapportering-och-fynd/oppna-data-och-apier/api-villkor/"


def tr(text):
    return QCoreApplication.translate("SpeciesDataDockWidget", text)


class SpeciesDataDockWidget(QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__(tr("Species Data (SLU Artdatabanken)"), parent)
        self.iface = iface
        self.setObjectName("SpeciesDataDockWidget")
        self._count = None  # (Query, Count) of the last count
        self._unknown = ()  # names in the last count that match nothing in the data
        self._aliases = {}  # Swedish genus name typed by the user -> scientific genus
        self._count_task = None
        self._execute_pending = False  # the button was pressed, waiting for the count
        self._downloading = False

        content = QWidget(self)
        layout = QVBoxLayout(content)
        sections = QWidget()
        sections_layout = QVBoxLayout(sections)
        for title, build in (
            (tr("Taxa"), self._taxa_tab),
            (tr("Time"), self._time_tab),
            (tr("Geography"), self._geography_tab),
            (tr("Properties"), self._properties_tab),
            (tr("Extra fields"), self._extra_fields_tab),
        ):
            box = QgsCollapsibleGroupBox(title)
            QVBoxLayout(box).addWidget(build())
            sections_layout.addWidget(box)
        sections_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(sections)
        layout.addWidget(scroll, 1)

        self.count_button = QPushButton(tr("Count observations"))
        self.count_button.clicked.connect(self._start_count)
        self.count_label = QLabel("")
        self.count_label.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.create_button = QPushButton(tr("Fetch and show observations"))
        self.create_button.clicked.connect(self.on_create)
        layout.addWidget(self.count_button)
        layout.addWidget(self.count_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.create_button)

        source = QLabel(
            tr(
                "Data: Artportalen, via SLU Artdatabanken, Species Observation System. "
                "Independent plugin, not owned or endorsed by SLU. "
                '<a href="{url}">Terms of use</a>.'
            ).format(url=TERMS_URL)
        )
        source.setWordWrap(True)
        source.setOpenExternalLinks(True)
        layout.addWidget(source)
        layout.addStretch()
        self.setWidget(content)
        self._watch_inputs(content)
        iface.mapCanvas().extentsChanged.connect(self._map_moved)
        self._clear_count()

    def _watch_inputs(self, root):
        """Clear the count text when an input changes: it no longer describes the search."""
        signals = (
            (QPlainTextEdit, "textChanged"),
            (QComboBox, "currentIndexChanged"),
            (QCheckBox, "toggled"),
            (QRadioButton, "toggled"),
            (QSpinBox, "valueChanged"),
            (QDateEdit, "dateChanged"),
        )
        for widget_type, signal in signals:
            for widget in root.findChildren(widget_type):
                getattr(widget, signal).connect(self._clear_count)

    def _clear_count(self, *_):
        """The inputs changed: the old count no longer describes the search."""
        self._execute_pending = False
        self._stop_count()
        self._count = None
        self._unknown = ()
        self.count_label.setText("")

    def _stop_count(self):
        if self._count_task is not None:
            self._count_task.cancel()
            self._count_task = None
        self.progress.setVisible(False)
        self.count_button.setEnabled(True)

    def _map_moved(self):
        # The search is for the map window at the time of the click: let it finish.
        if self.area_canvas.isChecked() and not (self._execute_pending or self._downloading):
            self._clear_count()

    def _start_count(self):
        query = self.build_query()
        self.count_button.setEnabled(False)
        self.count_label.setText(tr("Counting observations..."))
        self.progress.setRange(0, 0)  # busy: the number of requests is not known in advance
        self.progress.setVisible(True)

        def done(result, unknown, aliases):
            if task is not self._count_task:
                return  # superseded by a newer search
            self._count_task = None
            self.progress.setVisible(False)
            self.count_button.setEnabled(True)
            self._aliases.update(aliases)
            self._count = (self.build_query(), result)  # the query now uses the aliases
            self._unknown = unknown
            self._show_count(result)
            if self._execute_pending:
                self._execute_pending = False
                self._proceed(query, result)

        def failed(message):
            if task is self._count_task:
                self._count_task = None
                self._execute_pending = False
                self.progress.setVisible(False)
                self.count_button.setEnabled(True)
                self.create_button.setEnabled(True)
                self.count_label.setText(message)

        task = CountTask(query, done, failed)
        self._count_task = task
        QgsApplication.taskManager().addTask(task)

    # -- tabs --------------------------------------------------------------

    def _taxa_tab(self):
        tab = QWidget()
        form = QVBoxLayout(tab)
        scope = QLabel(tr("This version searches vascular plants (Kärlväxter) only."))
        scope.setWordWrap(True)
        self.names = QPlainTextEdit()
        self.names.setMaximumHeight(80)
        self.names.setPlaceholderText(
            tr("One species name per line, scientific or Swedish\n(for example: vitsippa)")
        )
        form.addWidget(scope)
        form.addWidget(QLabel(tr(
            "Genus: Anemone or Anemone spp. (all species), Anemone sp. (genus level only). "
            "Wildcard: anem*"
        )))
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
        box_layout = QGridLayout(box)
        self.redlist = {}
        for i, code in enumerate(REDLIST_CATEGORIES):
            check = QCheckBox(code)
            self.redlist[code] = check
            box_layout.addWidget(check, i // 5, i % 5)
        threatened = QPushButton(tr("CR, EN, VU, NT"))
        threatened.clicked.connect(self._select_threatened)
        box_layout.addWidget(threatened, 2, 0, 1, 5)
        layout.addWidget(box)
        layout.addStretch()
        return tab

    def _select_threatened(self):
        for code, box in self.redlist.items():
            box.setChecked(code in THREATENED_CATEGORIES)

    def _extra_fields_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel(tr("The standard fields are always included.")))
        self.extras = {}
        for key, label in EXTRA_FIELD_LABELS:
            check = QCheckBox(tr(label))
            self.extras[key] = check
            layout.addWidget(check)
        layout.addStretch()
        return tab

    # -- query -------------------------------------------------------------

    def build_query(self) -> Query:
        names = tuple(
            self._aliases.get(line.strip(), line.strip())
            for line in self.names.toPlainText().splitlines()
            if line.strip()
        )
        date_from, date_to = self._period()
        bbox = self._canvas_bbox() if self.area_canvas.isChecked() else None
        return Query(
            organism_group=DEFAULT_ORGANISM_GROUP,
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
            dataset_ids=(ARTPORTALEN,),
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
        for typed, genus in self._aliases.items():
            if typed in self.names.toPlainText().split("\n"):
                note = tr("{name} is the genus {genus}: all its species are included.")
                text += "\n" + note.format(name=typed, genus=genus)
        if self._unknown:
            warning = tr("No vascular plant has the name: {names}. Check the spelling.")
            text += "\n" + warning.format(names=", ".join(self._unknown))
        self.count_label.setText(text)
        return assessment

    def on_create(self):
        """Fetch and show: count first (if needed), then download and add the layer."""
        query = self.build_query()
        self.create_button.setEnabled(False)
        if self._count is not None and self._count[0] == query:
            self._proceed(query, self._count[1])
            return
        self._execute_pending = True
        if self._count_task is None:
            self._start_count()

    def _proceed(self, query, result):
        assessment = self._show_count(result)
        if result.value == 0:
            self.create_button.setEnabled(True)
            QMessageBox.information(
                self, tr("Species Data"), tr("No observations match the search.")
            )
            return
        if assessment.at_least:
            self.create_button.setEnabled(True)
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
                tr("About {n} observations will be fetched. Continue?").format(n=result.value),
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.create_button.setEnabled(True)
                return
        self._download(query, result)

    def _download(self, query, result):
        extras = tuple(key for key, box in self.extras.items() if box.isChecked())
        fields = snapshot.fields_for(query, extras)
        name = self._layer_name(query, result)
        self._downloading = True
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.count_label.setText(tr("Fetching and showing observations..."))

        def finish():
            self._downloading = False
            self.create_button.setEnabled(True)
            self.progress.setVisible(False)

        def done(rows):
            finish()
            layer = layers.create_layer(rows, fields, query, name, result)
            if layer is None:
                self._show_count(result)
                QMessageBox.warning(self, tr("Species Data"), tr("The layer could not be created."))
                return
            QgsProject.instance().addMapLayer(layer)
            self.count_label.setText(tr("Showing {n} observations.").format(n=len(rows)))
            self.iface.messageBar().pushMessage(
                tr("Species Data"), provenance.citation(datetime.now()), duration=8
            )

        def failed(message):
            finish()
            self._show_count(result)
            QMessageBox.warning(self, tr("Species Data"), message)

        def progressed(value):
            self.progress.setValue(int(value))
            fetched = int(result.value * value / 100)
            self.count_label.setText(
                tr("Fetching and showing observations: {done} of {total}").format(
                    done=fetched, total=result.value
                )
            )

        self._task = SnapshotTask(query, fields, result.value, done, failed)
        self._task.progressChanged.connect(progressed)
        self._task.taskTerminated.connect(lambda: (finish(), self._show_count(result)))
        QgsApplication.taskManager().addTask(self._task)

    @staticmethod
    def _layer_name(query, result):
        what = ", ".join(query.names) if query.names else (query.organism_group or tr("Species"))
        return f"{what} ({result.value})"
