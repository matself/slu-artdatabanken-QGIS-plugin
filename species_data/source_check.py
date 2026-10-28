"""Is a layer a data set this plugin fetched? (no QGIS imports)

The plugin writes its source line into the layer metadata, and QGIS keeps that metadata when
the layer is saved to a GeoPackage (and reads it back when the file is opened). Together with
the fields that the clustering needs it tells a plugin layer from any other point layer.
"""
from . import provenance

# Fields the clustering reads. The first four are always downloaded (snapshot.CORE_FIELDS).
REQUIRED_FIELDS = ("occurrenceId", "scientificName", "endDate", "coordinateUncertaintyInMeters")


NOT_POINT = "not_point"
MISSING_FIELDS = "missing_fields"
NO_SOURCE = "no_source"
EMPTY = "empty"


def problems(field_names, abstract: str, is_point: bool, feature_count: int) -> list:
    """What is wrong with the layer, as (code, detail) pairs. Empty when it is usable."""
    found = []
    if not is_point:
        found.append((NOT_POINT, ""))
    missing = [name for name in REQUIRED_FIELDS if name not in field_names]
    if missing:
        found.append((MISSING_FIELDS, ", ".join(missing)))
    if provenance.SOURCE not in (abstract or ""):
        found.append((NO_SOURCE, ""))
    if feature_count == 0:
        found.append((EMPTY, ""))
    return found
