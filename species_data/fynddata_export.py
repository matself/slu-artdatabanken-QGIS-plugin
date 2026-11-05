"""Read an export from SLU's Fynddata and turn it into the rows of a layer (no QGIS imports).

Fynddata can save a search as a GeoJSON file with one property per column. Only the columns
that match fields the plugin creates itself are read. Everything else, in particular the
observer and other personal data, is never looked at. The files that come with the export
(``filter.md``, ``citation.md`` and ``datasets.md``) describe what the file contains and are
read when they belong to the same export.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import provenance, snapshot, source_check
from .snapshot import Row

# The fields of the layer made from an export: those of a fetched layer that an export can
# fill. ``url`` and ``isVerified`` are left empty (the export has a GUID but no link, and its
# verification status is a text with several values).
FIELDS = tuple(
    pair for pair in snapshot.CORE_FIELDS if pair[0] not in ("url", "isVerified")
) + (
    ("isPresentObservation", "bool"),
    ("isNotRediscoveredObservation", "bool"),
    ("isUncertainIdentification", "bool"),
)

# Layer field -> column of the export, per language of the Fynddata interface.
COLUMNS = {
    "sv": {
        "occurrenceId": "Observation GUID",
        "scientificName": "Vetenskapligt namn",
        "vernacularName": "Svenskt namn",
        "startDate": "Startdatum",
        "endDate": "Slutdatum",
        "locality": "Lokal",
        "municipality": "Kommun",
        "county": "Län",
        "province": "Landskap",
        "coordinateUncertaintyInMeters": "Koordinatnoggrannhet (m)",
        "redlistCategory": "Rödlistekategori",
        "organismQuantity": "Organismkvantitet",
        "organismQuantityUnit": "Organismkvantitetsenhet",
        "datasetName": "Dataset namn",
        "isNotRediscoveredObservation": "Ej återfunnen",
        "isUncertainIdentification": "Osäker artbestämning",
        # Inverted: "not found" true means the species was searched for and not seen.
        "isPresentObservation": "Ej funnen",
    },
}

# Above this many observations the user is asked before the layer is made.
LARGE = 100000


@dataclass
class Mapping:
    language: str
    columns: dict  # layer field -> column found in the file
    missing: tuple  # layer fields that the file lacks and the plugin needs


def match_columns(columns) -> Optional[Mapping]:
    """The language of the export and which columns match, or None when it is not an export.

    A file is taken for an export when it has the column of every required field in one of
    the known languages.
    """
    present = set(columns)
    best = None
    for language, names in COLUMNS.items():
        found = {field: column for field, column in names.items() if column in present}
        missing = tuple(f for f in source_check.REQUIRED_FIELDS if f not in found)
        candidate = Mapping(language, found, missing)
        if not missing:
            return candidate
        if best is None or len(found) > len(best.columns):
            best = candidate
    return best if best and best.columns else None


def read_features(path) -> list:
    """The features of a GeoJSON file. Raises ValueError when it is not a feature collection."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    features = data.get("features") if isinstance(data, dict) else None
    if not isinstance(features, list):
        raise ValueError("not a GeoJSON feature collection")
    return features


def columns_of(features) -> set:
    """The property names used by the first features (all features of an export share them)."""
    names = set()
    for feature in features[:50]:
        names.update((feature.get("properties") or {}).keys())
    return names


def build_rows(features, mapping: Mapping, transform: Callable) -> list:
    """Rows with the layer fields filled from the mapped columns.

    ``transform(lon, lat)`` gives the coordinates of the layer (SWEREF 99 TM). Features
    without a point are skipped, and so are observations of absence ("not found").
    """
    rows = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            continue
        properties = feature.get("properties") or {}
        values = {}
        for field, _kind in FIELDS:
            column = mapping.columns.get(field)
            values[field] = properties.get(column) if column else None
        not_found = values["isPresentObservation"]
        values["isPresentObservation"] = None if not_found is None else not bool(not_found)
        if values["isPresentObservation"] is False and not values["isNotRediscoveredObservation"]:
            continue  # an observation of absence says nothing about where it grows
        lon, lat = geometry["coordinates"][:2]
        x, y = transform(lon, lat)
        rows.append(Row(values, x, y))
    return rows


# -- the files that come with the export ---------------------------------------------------

_STAMP_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})[ _](\d{2})[.:](\d{2})")
_STAMP_IN_TEXT = re.compile(r"(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2})")


@dataclass
class Sidecars:
    filter_text: str = ""
    citation_text: str = ""
    datasets: tuple = ()  # (dataset, observations in the file) with at least one observation
    stamp: str = ""  # "2026-11-05 15:33", from the file name
    other_exports: tuple = ()  # files found whose time does not match the export


def stamp_of_name(name: str) -> str:
    found = _STAMP_IN_NAME.search(name)
    return f"{found.group(1)} {found.group(2)}:{found.group(3)}" if found else ""


def _stamp_of_text(text: str) -> str:
    found = _STAMP_IN_TEXT.search(text.splitlines()[0] if text else "")
    return f"{found.group(1)} {found.group(2)}:{found.group(3)}" if found else ""


def read_sidecars(path) -> Sidecars:
    """Read ``filter.md``, ``citation.md`` and ``datasets.md`` from the folder of the export.

    The files have the same names in every export, so one is only used when the time in its
    heading is the time in the name of the export file. The others are reported.
    """
    path = Path(path)
    result = Sidecars(stamp=stamp_of_name(path.name))
    other = []
    for name in ("filter.md", "citation.md", "datasets.md"):
        file = path.with_name(name)
        if not file.is_file():
            continue
        text = file.read_text(encoding="utf-8", errors="replace")
        if not result.stamp or _stamp_of_text(text) != result.stamp:
            other.append(name)
            continue
        if name == "filter.md":
            result.filter_text = text.strip()
        elif name == "citation.md":
            result.citation_text = text.strip()
        else:
            result.datasets = _datasets_in_file(text)
    result.other_exports = tuple(other)
    return result


def _datasets_in_file(text: str) -> tuple:
    found = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[3].isdigit() and int(cells[3]) > 0:
            found.append((cells[0], int(cells[3])))
    return tuple(sorted(found, key=lambda item: -item[1]))


def layer_name(path, count: int) -> str:
    stamp = stamp_of_name(Path(path).name).replace(":", ".")
    return f"Fynddata {stamp} ({count})" if stamp else f"{Path(path).stem} ({count})"


def abstract(path, count: int, sidecars: Sidecars, imported: str) -> str:
    """The layer abstract. It names the source, so the other tabs accept the layer."""
    lines = [
        f"Data: {provenance.SOURCE}, saved as an export from the tool Fynddata.",
        f"Opened by the plugin Species Data from the file {Path(path).name} on {imported}.",
        f"Number of observations: {count}.",
    ]
    if sidecars.datasets:
        lines += ["", "Datasets in the file: " + ", ".join(f"{name} ({n})" for name, n in sidecars.datasets)]
    if sidecars.filter_text:
        lines += ["", "Search filter of the export (filter.md):", sidecars.filter_text]
    else:
        lines += ["", "The search filter of the export was not read, so what the file contains is not described here."]
    if sidecars.citation_text:
        lines += ["", "Citation of the export (citation.md):", sidecars.citation_text]
    lines += ["", "Data providers may have different licences: see the datasetName field.", provenance.DISCLAIMER]
    return "\n".join(lines)
