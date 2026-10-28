"""Build the temporary observation layer. The user saves it with QGIS own tools."""
from datetime import datetime

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsFields,
    QgsFillSymbol,
    QgsGeometry,
    QgsGeometryGeneratorSymbolLayer,
    QgsLayerMetadata,
    QgsMarkerSymbol,
    QgsPointXY,
    QgsRuleBasedRenderer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication, QDate, QDateTime, QMetaType, Qt, QTimeZone
from qgis.PyQt.QtGui import QColor

from . import provenance, styles
from .counting import Count
from .query import Query
from .wfs import CRS

_TYPES = {
    "str": QMetaType.Type.QString,
    "int": QMetaType.Type.Int,
    "bool": QMetaType.Type.Bool,
    "date": QMetaType.Type.QDate,
}


def tr(text):
    return QCoreApplication.translate("Layers", text)


_STOCKHOLM = QTimeZone(b"Europe/Stockholm")

# Shown when the pointer rests on a point (QGIS map tips) and in the identify results.
DISPLAY_EXPRESSION = (
    "coalesce(\"vernacularName\", \"scientificName\") || ' ' || "
    "coalesce(format_date(\"endDate\", 'yyyy-MM-dd'), '')"
)
MAP_TIP = (
    "<b>[% coalesce(\"vernacularName\", '') %]</b> "
    "<i>[% coalesce(\"scientificName\", '') %]</i><br>"
    "[% coalesce(format_date(\"endDate\", 'yyyy-MM-dd'), '') %]<br>"
    "[% coalesce(\"locality\", '') %]"
    "[% if(\"organismQuantity\" is not null, "
    "'<br>' || \"organismQuantity\" || ' ' || coalesce(\"organismQuantityUnit\", ''), '') %]"
)


def create_layer(
    rows, fields: tuple, query: Query, name: str, count: Count, retrieved: datetime = None
):
    """The observations as a temporary (memory) layer.

    Nothing is written to disk. QGIS marks the layer as temporary and offers to make it
    permanent, or the user can export it with "Save Features As".
    """
    retrieved = retrieved or datetime.now()
    layer = _memory_layer(rows, fields)
    layer.setName(name)
    layer.setRenderer(_year_renderer(layer))
    layer.setDisplayExpression(DISPLAY_EXPRESSION)
    layer.setMapTipTemplate(MAP_TIP)
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


# The uncertainty circle is its own rule in the renderer, so it shows as one entry in the legend
# and can be switched off there. Every observation gets the same thin, unfilled circle whatever
# its year. The layer is in metres (SWEREF 99 TM). To keep the map readable the rule is only
# active when zoomed in to CIRCLE_MAX_SCALE or closer, and leaves out observations less precise
# than CIRCLE_MAX_METERS. The limits can be changed in the layer styling panel.
CIRCLE_MAX_METERS = 250
CIRCLE_MAX_SCALE = 10000
CIRCLE_COLOR = "#444444"
CIRCLE_FILTER = (
    f'"coordinateUncertaintyInMeters" > 0 and "coordinateUncertaintyInMeters" <= {CIRCLE_MAX_METERS}'
)


def _symbol(color):
    return QgsMarkerSymbol.createSimple(
        {"name": "circle", "color": color.name(), "size": "2.4", "outline_color": "#ffffff",
         "outline_width": "0.25"}
    )


def _circle_symbol():
    """A marker symbol whose only layer draws the buffer of the point, as an outline."""
    symbol = QgsMarkerSymbol.createSimple({"name": "circle", "size": "1"})
    generator = QgsGeometryGeneratorSymbolLayer.create(
        {"geometryModifier": 'buffer($geometry, "coordinateUncertaintyInMeters")'}
    )
    generator.setSymbolType(Qgis.SymbolType.Fill)
    generator.setSubSymbol(
        QgsFillSymbol.createSimple(
            {"style": "no", "outline_color": CIRCLE_COLOR, "outline_width": "0.2"}
        )
    )
    symbol.changeSymbolLayer(0, generator)
    return symbol


def _year_renderer(layer):
    """One colour per year of the end date, newest drawn on top, and the uncertainty circle."""
    years = set()
    for feature in layer.getFeatures():
        value = feature["endDate"]
        if isinstance(value, QDate) and value.isValid():
            years.add(value.year())
    rule = QgsRuleBasedRenderer.Rule
    root = rule(None)
    root.appendChild(
        rule(_circle_symbol(), 0, CIRCLE_MAX_SCALE, CIRCLE_FILTER, tr("Uncertainty"))
    )
    for year in sorted(years):
        color = QColor.fromHsvF(*styles.year_color_hsv(year))
        root.appendChild(rule(_symbol(color), 0, 0, f'year("endDate") = {year}', str(year)))
    root.appendChild(rule(_symbol(QColor(styles.NO_DATE_COLOR)), 0, 0, "ELSE", ""))
    renderer = QgsRuleBasedRenderer(root)
    request = QgsFeatureRequest.OrderBy([QgsFeatureRequest.OrderByClause('"endDate"', True)])
    renderer.setOrderBy(request)
    renderer.setOrderByEnabled(True)
    return renderer


def _metadata(query, name, count, retrieved):
    meta = QgsLayerMetadata()
    meta.setTitle(name)
    meta.setAbstract(provenance.abstract(query, count, retrieved))
    meta.setRights([provenance.citation(retrieved), provenance.DISCLAIMER])
    meta.setType("dataset")
    meta.setCrs(QgsCoordinateReferenceSystem(CRS))
    return meta
