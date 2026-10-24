"""Download logic for snapshot layers (no QGIS imports).

Features are fetched page by page with single GeoJSON requests, which can be
cancelled between pages, and only the fields listed here are requested: personal
fields such as ``recordedBy`` are never downloaded.
"""
import json
from dataclasses import dataclass
from typing import Callable, Optional

from .counting import CancelledError

# (WFS property, type) where type is one of: str, int, bool, date.
FIELDS = (
    ("occurrenceId", "str"),
    ("url", "str"),
    ("scientificName", "str"),
    ("vernacularName", "str"),
    ("dyntaxaTaxonId", "int"),
    ("organismGroup", "str"),
    ("startDate", "date"),
    ("endDate", "date"),
    ("county", "str"),
    ("municipality", "str"),
    ("locality", "str"),
    ("coordinateUncertaintyInMeters", "int"),
    ("isPresentObservation", "bool"),
    ("isNotRediscoveredObservation", "bool"),
    ("isNeverFoundObservation", "bool"),
    ("isVerified", "bool"),
    ("isUncertainIdentification", "bool"),
    ("redlistCategory", "str"),
    ("dataProviderId", "int"),
    ("datasetName", "str"),
    ("organismQuantity", "str"),
    ("organismQuantityUnit", "str"),
)
FIELD_NAMES = tuple(name for name, _ in FIELDS)

PAGE_SIZE = 1000


@dataclass(frozen=True)
class Row:
    properties: dict
    x: float
    y: float


def parse_page(text: str) -> list:
    """Rows of a GeoJSON page. Features without a point geometry are skipped."""
    rows = []
    for feature in json.loads(text).get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            continue
        x, y = geometry["coordinates"][:2]
        rows.append(Row({n: feature["properties"].get(n) for n in FIELD_NAMES}, x, y))
    return rows


def collect(
    fetch_page: Callable[[int, int], list],
    total: int,
    page_size: int = PAGE_SIZE,
    is_cancelled: Callable[[], bool] = lambda: False,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> list:
    """Fetch pages until ``total`` rows are expected or a page comes back short.

    ``fetch_page(start, size)`` returns the rows of one page. The data can shift
    between requests, so rows are de-duplicated on ``occurrenceId``. Raises
    ``CancelledError`` when ``is_cancelled`` turns true.
    """
    rows = {}
    start = 0
    while start < total:
        if is_cancelled():
            raise CancelledError()
        page = fetch_page(start, page_size)
        for row in page:
            rows.setdefault(row.properties["occurrenceId"], row)
        start += page_size
        if on_progress:
            on_progress(min(start, total), total)
        if len(page) < page_size:
            break
    return list(rows.values())
