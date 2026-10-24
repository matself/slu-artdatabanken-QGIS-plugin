"""Build the snapshot layer: a GeoPackage with the downloaded observations."""
from datetime import datetime
from pathlib import Path

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsLayerMetadata,
    QgsMarkerSymbol,
    QgsPointXY,
    QgsSingleSymbolRenderer,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QDateTime, QMetaType, Qt, QTimeZone

from . import provenance, snapshot
from .counting import Count
from .query import Query
from .wfs import CRS, PERSONAL_FIELDS, layer_uri

_TYPES = {
    "str": QMetaType.Type.QString,
    "int": QMetaType.Type.Int,
    "bool": QMetaType.Type.Bool,
    "date": QMetaType.Type.QDate,
}
_STOCKHOLM = QTimeZone(b"Europe/Stockholm")


def snapshot_folder() -> Path:
    folder = Path(QgsApplication.qgisSettingsDirPath()) / "species_data" / "snapshots"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def create_live_layer(
    query: Query, name: str, count: Count, follow_map: bool, retrieved: datetime = None
):
    """A WFS layer that fetches on demand: only the map window when ``follow_map``.

    Returns None when the provider could not open it. The query must not carry the
    map window itself: QGIS adds it to each request.
    """
    retrieved = retrieved or datetime.now()
    layer = QgsVectorLayer(layer_uri(query.to_qgis_expression(), follow_map), name, "WFS")
    if not layer.isValid():
        return None
    layer.setRenderer(QgsSingleSymbolRenderer(_symbol()))
    layer.setMetadata(_metadata(query, name, count, retrieved))
    _hide_personal_fields(layer)
    return layer


def _hide_personal_fields(layer):
    """Hide fields with personal data in the attribute table.

    The provider lower-cases the field names and adds a ``*_nil`` field for each. The
    data is still downloaded; snapshot layers never request it.
    """
    personal = tuple(name.lower() for name in PERSONAL_FIELDS)
    config = layer.attributeTableConfig()
    config.update(layer.fields())
    columns = config.columns()
    for column in columns:
        if column.name.lower().startswith(personal):
            column.hidden = True
    config.setColumns(columns)
    layer.setAttributeTableConfig(config)


def create_snapshot_layer(rows, query: Query, name: str, count: Count, retrieved: datetime = None):
    """Write ``rows`` to a new GeoPackage and return it as a layer, or None on failure."""
    retrieved = retrieved or datetime.now()
    memory = _memory_layer(rows)
    path = snapshot_folder() / f"observations_{retrieved:%Y%m%d_%H%M%S}.gpkg"
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = "observations"
    error, *_ = QgsVectorFileWriter.writeAsVectorFormatV3(
        memory, str(path), QgsCoordinateTransformContext(), options
    )
    if error != QgsVectorFileWriter.WriterError.NoError:
        return None
    layer = QgsVectorLayer(f"{path}|layername=observations", name, "ogr")
    if not layer.isValid():
        return None
    layer.setRenderer(QgsSingleSymbolRenderer(_symbol()))
    layer.setMetadata(_metadata(query, name, count, retrieved))
    return layer


def _memory_layer(rows):
    layer = QgsVectorLayer(f"Point?crs={CRS}", "observations", "memory")
    fields = QgsFields()
    for field_name, kind in snapshot.FIELDS:
        fields.append(QgsField(field_name, _TYPES[kind]))
    layer.dataProvider().addAttributes(list(fields))
    layer.updateFields()
    features = []
    for row in rows:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(row.x, row.y)))
        feature.setAttributes([_convert(row.properties[n], k) for n, k in snapshot.FIELDS])
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    return layer


def _convert(value, kind):
    if value is None:
        return None
    if kind == "date":
        moment = QDateTime.fromString(value, Qt.DateFormat.ISODate)
        return moment.toTimeZone(_STOCKHOLM).date() if moment.isValid() else None
    return value


def _symbol():
    return QgsMarkerSymbol.createSimple(
        {"name": "circle", "color": "#d95f02", "size": "2.4", "outline_color": "#ffffff",
         "outline_width": "0.25"}
    )


def _metadata(query, name, count, retrieved):
    meta = QgsLayerMetadata()
    meta.setTitle(name)
    meta.setAbstract(provenance.abstract(query, count, retrieved))
    meta.setRights([provenance.citation(retrieved), provenance.DISCLAIMER])
    meta.setType("dataset")
    meta.setCrs(QgsCoordinateReferenceSystem(CRS))
    return meta
