"""Source and query description stored in the layer metadata (no QGIS imports)."""
from datetime import datetime

from .counting import Count
from .query import Query

SOURCE = "SLU Artdatabanken, Species Observation System"
DISCLAIMER = (
    "Created with the independent plugin Species Data (SLU Artdatabanken). "
    "The plugin is not developed, owned or endorsed by SLU."
)


def citation(retrieved: datetime) -> str:
    return f"Data: {SOURCE}, retrieved {retrieved:%Y-%m-%d} via the open WFS service."


def describe(query: Query) -> list:
    """Human readable lines describing the filters of a query."""
    lines = []
    if query.organism_group:
        lines.append(f"Organism group: {query.organism_group}")
    if query.names:
        lines.append("Names: " + ", ".join(query.names))
    if query.county:
        lines.append(f"County: {query.county}")
    if query.municipality:
        lines.append(f"Municipality: {query.municipality}")
    if query.bbox_wgs84:
        b = query.bbox_wgs84
        lines.append(f"Bounding box (WGS84): {b.west:.5f},{b.south:.5f},{b.east:.5f},{b.north:.5f}")
    if query.date_from or query.date_to:
        lines.append(f"Period: {query.date_from or '...'} to {query.date_to or '...'}")
    lines.append(f"Occurrence: {query.occurrence}")
    if query.redlist_categories:
        lines.append("Red list categories: " + ", ".join(query.redlist_categories))
    if query.dataset_ids:
        lines.append("Data provider ids: " + ", ".join(str(i) for i in query.dataset_ids))
    if query.max_uncertainty_m is not None:
        lines.append(f"Max coordinate uncertainty: {query.max_uncertainty_m} m")
    if query.exclude_uncertain_identification:
        lines.append("Uncertain identifications excluded")
    if query.verified_only:
        lines.append("Verified observations only")
    return lines


def abstract(query: Query, count: Count, retrieved: datetime) -> str:
    amount = f"{count.value}" if count.exact else f"at least {count.value}"
    parts = [
        citation(retrieved),
        f"Number of observations when counted: {amount} (approximate).",
        "",
        *describe(query),
        "",
        "Data providers may have different licences: see the datasetName field.",
        DISCLAIMER,
    ]
    return "\n".join(parts)
