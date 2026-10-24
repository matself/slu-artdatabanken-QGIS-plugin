"""Create the observation layer from a query."""
from datetime import datetime

from qgis.core import (
    QgsLayerMetadata,
    QgsMarkerSymbol,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
)

from . import provenance
from .counting import Count
from .query import Query
from .wfs import PERSONAL_FIELDS, layer_uri


def create_layer(query: Query, name: str, count: Count, retrieved: datetime = None):
    """Return a WFS point layer, or None when the provider could not open it."""
    retrieved = retrieved or datetime.now()
    layer = QgsVectorLayer(layer_uri(query), name, "WFS")
    if not layer.isValid():
        return None
    layer.setRenderer(QgsSingleSymbolRenderer(_symbol()))
    layer.setMetadata(_metadata(query, name, count, retrieved))
    _hide_personal_fields(layer)
    return layer


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
    return meta


def _hide_personal_fields(layer):
    """Hide fields with personal data in the attribute table.

    The provider lower-cases the field names and adds a ``*_nil`` field for each.
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


__all__ = ["create_layer"]
