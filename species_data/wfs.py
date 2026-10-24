"""Pure helpers for the open SOS WFS service (no QGIS imports)."""
from .query import WFS_PAGING_LIMIT, Query

WFS_URL = "https://sosgeo.artdata.slu.se/geoserver/SOS/ows"
TYPE_NAME = "SOS:SpeciesObservations"
# Only version 1.0.0 works since the 2024 GeoServer upgrade.
WFS_VERSION = "1.0.0"
CRS = "EPSG:3006"

# Fields holding personal data. The plugin hides them in the attribute table.
PERSONAL_FIELDS = ("recordedBy", "reportedBy")
GEOMETRY_FIELD = "point"


def request_params(
    query: Query, start_index: int = 0, max_features: int = 1, fields: tuple = ()
) -> dict:
    """GetFeature parameters for a GeoJSON request.

    Without ``fields`` only the id is returned (a light probe). With ``fields`` those
    properties plus the geometry are returned; personal fields are simply not asked for.
    """
    params = {
        "service": "WFS",
        "version": WFS_VERSION,
        "request": "GetFeature",
        "typeName": TYPE_NAME,
        "outputFormat": "application/json",
        "srsName": CRS,
        "maxFeatures": str(max_features),
        "startIndex": str(start_index),
        "propertyName": ",".join((*fields, GEOMETRY_FIELD)) if fields else "occurrenceId",
    }
    ogc_filter = query.to_ogc_filter()
    if ogc_filter:
        params["filter"] = ogc_filter
    return params


__all__ = ["WFS_PAGING_LIMIT", "request_params"]
