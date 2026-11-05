"""Open an export from Fynddata and make a layer of it, like the layer a fetch makes.

The layer has the fields of a fetched layer and the same style, so the Localities and
Co-occurrence tabs work on it unchanged. Nothing is written to disk.
"""
from datetime import datetime
from html import escape
from pathlib import Path

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
)
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from . import fynddata_export as export
from . import layers
from .counting import Count
from .wfs import CRS


def tr(text):
    return QCoreApplication.translate("ExportDialog", text)


class SummaryDialog(QDialog):
    """What was found in the file, before anything is made."""

    def __init__(self, html: str, can_create: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Open an export from Fynddata"))
        layout = QVBoxLayout(self)
        label = QLabel(html)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        layout.addWidget(label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        create = buttons.addButton(tr("Create layer"), QDialogButtonBox.ButtonRole.AcceptRole)
        create.setEnabled(can_create)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setMinimumWidth(480)


def summary_html(path, features, mapping, sidecars) -> str:
    """The text of the dialog."""
    parts = [f"<b>{escape(Path(path).name)}</b><br>{tr('{n} observations').format(n=len(features))}"]
    if mapping is None:
        parts.append(tr("This does not look like an export from Fynddata: none of its columns are recognised."))
        return "<br><br>".join(parts)
    if mapping.missing:
        parts.append(
            tr("These columns are missing, so the file cannot be used: {fields}.").format(
                fields=escape(", ".join(mapping.missing))
            )
        )
    else:
        read = ", ".join(escape(column) for column in mapping.columns.values())
        parts.append(tr("Columns that are read: {columns}.").format(columns=read))
        parts.append(tr("Other columns, including the observer, are not read."))
    if sidecars.filter_text:
        parts.append(
            tr("The search filter, citation and datasets of the export were found and are put in the layer metadata.")
        )
    elif sidecars.other_exports:
        parts.append(
            tr("{files} next to the file belong to another export and are not used.").format(
                files=escape(", ".join(sidecars.other_exports))
            )
        )
    else:
        parts.append(tr("The files filter.md, citation.md and datasets.md were not found next to the file."))
    return "<br><br>".join(parts)


def open_export(iface, parent=None):
    """Ask for an export file, show what it holds and add the layer when the user agrees."""
    path, _ = QFileDialog.getOpenFileName(
        parent, tr("Open an export from Fynddata"), "", tr("GeoJSON (*.geojson *.json)")
    )
    if not path:
        return None
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        features = export.read_features(path)
    except (OSError, ValueError) as exc:
        QApplication.restoreOverrideCursor()
        QMessageBox.warning(parent, tr("Species Data"), tr("The file could not be read: {why}").format(why=exc))
        return None
    QApplication.restoreOverrideCursor()
    mapping = export.match_columns(export.columns_of(features))
    sidecars = export.read_sidecars(path)
    dialog = SummaryDialog(
        summary_html(path, features, mapping, sidecars),
        mapping is not None and not mapping.missing and bool(features),
        parent,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    if len(features) > export.LARGE:
        answer = QMessageBox.question(
            parent,
            tr("Species Data"),
            tr(
                "The file has {n} observations. A map of that many points is slow, "
                "and grouping takes a while. Continue?"
            ).format(n=len(features)),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return None
    layer = make_layer(path, features, mapping, sidecars)
    if layer is None:
        QMessageBox.warning(parent, tr("Species Data"), tr("The layer could not be created."))
        return None
    QgsProject.instance().addMapLayer(layer)
    iface.setActiveLayer(layer)
    return layer


def make_layer(path, features, mapping, sidecars):
    """The temporary layer of an export."""
    transform = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"), QgsCoordinateReferenceSystem(CRS), QgsProject.instance()
    )

    def to_layer_crs(lon, lat):
        point = transform.transform(lon, lat)
        return point.x(), point.y()

    rows = export.build_rows(features, mapping, to_layer_crs)
    name = export.layer_name(path, len(rows))
    text = export.abstract(path, len(rows), sidecars, f"{datetime.now():%Y-%m-%d}")
    rights = [part for part in (sidecars.citation_text,) if part]
    return layers.create_layer(
        rows, export.FIELDS, None, name, Count(len(rows), True), abstract=text, rights=rights
    )
