"""Build the observation layer: temporary, or saved as a GeoPackage where the user chose."""
from datetime import datetime

from qgis.core import (
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

from . import provenance
from .counting import Count
from .query import Query
from .wfs import CRS

_TYPES = {
    "str": QMetaType.Type.QString,
    "int": QMetaType.Type.Int,
    "bool": QMetaType.Type.Bool,
    "date": QMetaType.Type.QDate,
}
_STOCKHOLM = QTimeZone(b"Europe/Stockholm")


def create_snapshot_layer(
    rows,
    fields: tuple,
    query: Query,
    name: str,
    count: Count,
    path: str = "",
    retrieved: datetime = None,
):
    """The observations as a layer, or None on failure.

    With ``path`` the layer is written to that GeoPackage (replacing the file). Without
    it the layer is temporary: QGIS marks it and offers to save it permanently.
    """
    retrieved = retrieved or datetime.now()
    layer = _memory_layer(rows, fields)
    if path:
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = "observations"
        error, *_ = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, path, QgsCoordinateTransformContext(), options
        )
        if error != QgsVectorFileWriter.WriterError.NoError:
            return None
        layer = QgsVectorLayer(f"{path}|layername=observations", name, "ogr")
        if not layer.isValid():
            return None
    layer.setName(name)
    layer.setRenderer(QgsSingleSymbolRenderer(_symbol()))
    layer.setMetadata(_metadata(query, name, count, retrieved))
    return layer


def _memory_layer(rows, fields):
    layer = QgsVectorLayer(f"Point?crs={CRS}", "observations", "memory")
    schema = QgsFields()
    for field_name, kind in fields:
        schema.append(QgsField(field_name, _TYPES[kind]))
    layer.dataProvider().addAttributes(list(schema))
    layer.updateFields()
    features = []
    for row in rows:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(row.x, row.y)))
        feature.setAttributes([_convert(row.properties[n], k) for n, k in fields])
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
