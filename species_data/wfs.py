"""Pure helpers for the open SOS WFS service (no QGIS imports)."""
from .query import WFS_PAGING_LIMIT, Query

WFS_URL = "https://sosgeo.artdata.slu.se/geoserver/SOS/ows"
TYPE_NAME = "SOS:SpeciesObservations"
# Only version 1.0.0 works since the 2024 GeoServer upgrade.
WFS_VERSION = "1.0.0"
CRS = "EPSG:3006"

# Fields holding personal data. The plugin hides them in the attribute table.
PERSONAL_FIELDS = ("recordedBy", "reportedBy")


def request_params(query: Query, start_index: int = 0, max_features: int = 1) -> dict:
    """GetFeature parameters for a light GeoJSON probe request."""
    params = {
        "service": "WFS",
        "version": WFS_VERSION,
        "request": "GetFeature",
        "typeName": TYPE_NAME,
        "outputFormat": "application/json",
        "srsName": CRS,
        "maxFeatures": str(max_features),
        "startIndex": str(start_index),
        "propertyName": "occurrenceId",
    }
    ogc_filter = query.to_ogc_filter()
    if ogc_filter:
        params["filter"] = ogc_filter
    return params


def layer_uri(query: Query, page_size: int = 1000) -> str:
    """QGIS WFS provider URI for a layer that pages through the result."""
    parts = {
        "url": WFS_URL,
        "typename": TYPE_NAME,
        "version": WFS_VERSION,
        "srsname": CRS,
        "pagingEnabled": "true",
        "pageSize": str(page_size),
    }
    ogc_filter = query.to_ogc_filter()
    if ogc_filter:
        parts["filter"] = ogc_filter
    return " ".join(f"{key}={_uri_quote(value)}" for key, value in parts.items())


def _uri_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\'") + "'"


__all__ = ["WFS_PAGING_LIMIT", "layer_uri", "request_params"]
