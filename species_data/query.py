"""Neutral observation query model.

One ``Query`` serialises to an OGC XML filter for the open WFS service and to a
``SearchFilterDto`` JSON body for the SOS REST API. This module has no QGIS or
network dependencies so it can be unit tested anywhere.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional
from xml.sax.saxutils import escape

# Paging on the WFS works up to this start index. One request returns at most 5000
# features and reports that as ``numberMatched`` even when more exist, so that number is
# never a total: counting probes with start indexes instead (see counting.py).
WFS_PAGING_LIMIT = 100000
# Warn the user well before the limit. A dot map of this many points is already
# too much to be useful.
WARN_THRESHOLD = 2000

DEFAULT_ORGANISM_GROUP = "Kärlväxter"

# All red list categories, in the order the UI shows them. The WFS
# ``isRedlisted`` flag is not used: it is also true for category NE.
REDLIST_CATEGORIES = ("RE", "CR", "EN", "VU", "NT", "DD", "LC", "NA", "NE")
# The default selection for "red-listed species".
THREATENED_CATEGORIES = ("CR", "EN", "VU", "NT")

PRESENT = "present"
ABSENT = "absent"
BOTH = "both"
_OCCURRENCE_REST = {PRESENT: "Present", ABSENT: "Absent", BOTH: "BothPresentAndAbsent"}

# Dates are stored as UTC instants of Swedish local time, so a date-only
# observation on local day D has startDate ~ (D-1)T22:00Z/23:00Z and endDate
# ~ DT21:59:59Z/22:59:59Z. These bounds keep whole local days in range.
_END_OF_DAY_START_BOUND = "T21:00:00Z"


_NS = 'xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml"'
_GEOMETRY_FIELD = "point"


class UnsupportedFilterError(ValueError):
    """The query uses a filter the chosen backend cannot express."""


@dataclass(frozen=True)
class BoundingBoxWgs84:
    west: float
    south: float
    east: float
    north: float


@dataclass(frozen=True)
class Query:
    """What the user wants to see.

    ``names`` are matched case-insensitively and exactly against both the
    scientific and the Swedish name. The spatial restriction (``bbox_wgs84``
    from the map canvas, or ``polygon_wgs84``) is part of the filter.
    """

    organism_group: Optional[str] = DEFAULT_ORGANISM_GROUP
    taxon_ids: tuple[int, ...] = ()
    names: tuple[str, ...] = ()
    county: Optional[str] = None
    municipality: Optional[str] = None
    bbox_wgs84: Optional[BoundingBoxWgs84] = None
    polygon_wgs84: Optional[dict] = None  # GeoJSON geometry in WGS84
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    occurrence: str = PRESENT
    verified_only: bool = False
    redlist_categories: tuple[str, ...] = ()
    dataset_ids: tuple[int, ...] = ()
    exclude_uncertain_identification: bool = False
    max_uncertainty_m: Optional[int] = None

    # -- WFS ---------------------------------------------------------------

    def to_ogc_filter(self) -> str:
        """OGC XML filter for the WFS ``filter`` / ``FILTER`` parameter.

        CQL cannot be used here: WFS refuses ``bbox`` together with
        ``CQL_FILTER`` and its CQL parser fails on ``BBOX``/``INTERSECTS``.
        An OGC filter carries the spatial restriction in the same expression.
        Returns an empty string when the query has no restrictions.
        """
        terms = []
        if self.organism_group:
            terms.append(_eq("organismGroup", self.organism_group))
        if self.taxon_ids:
            terms.append(_or([_eq("dyntaxaTaxonId", int(i)) for i in self.taxon_ids]))
        if self.names:
            terms.append(
                _or(
                    [
                        _like(field, name)
                        for name in self.names
                        for field in ("scientificName", "vernacularName")
                    ]
                )
            )
        if self.county:
            terms.append(_eq("county", self.county))
        if self.municipality:
            terms.append(_eq("municipality", self.municipality))
        if self.bbox_wgs84:
            terms.append(_bbox(self.bbox_wgs84))
        if self.polygon_wgs84:
            terms.append(_intersects(self.polygon_wgs84))
        if self.date_from:
            terms.append(_cmp("PropertyIsGreaterThanOrEqualTo", "endDate",
                              f"{self.date_from.isoformat()}T00:00:00Z"))
        if self.date_to:
            terms.append(_cmp("PropertyIsLessThanOrEqualTo", "startDate",
                              f"{self.date_to.isoformat()}{_END_OF_DAY_START_BOUND}"))
        if self.occurrence == PRESENT:
            terms.append(_eq("isPresentObservation", "true"))
        elif self.occurrence == ABSENT:
            terms.append(_eq("isPresentObservation", "false"))
        if self.dataset_ids:
            terms.append(_or([_eq("dataProviderId", int(i)) for i in self.dataset_ids]))
        if self.verified_only:
            terms.append(_eq("isVerified", "true"))
        if self.redlist_categories:
            terms.append(_or([_eq("redlistCategory", c) for c in self.redlist_categories]))
        if self.exclude_uncertain_identification:
            terms.append(_eq("isUncertainIdentification", "false"))
        if self.max_uncertainty_m is not None:
            terms.append(_cmp("PropertyIsLessThanOrEqualTo", "coordinateUncertaintyInMeters",
                              int(self.max_uncertainty_m)))
        if not terms:
            return ""
        body = terms[0] if len(terms) == 1 else "<ogc:And>" + "".join(terms) + "</ogc:And>"
        return f"<ogc:Filter {_NS}>{body}</ogc:Filter>"

    # -- REST --------------------------------------------------------------

    def to_sos_filter(self) -> dict:
        """``SearchFilterDto`` body for ``POST /Observations/Search``.

        The REST filter has no organism group or area-by-name filter, so such a
        query must be expressed with taxon ids; otherwise this raises rather
        than silently dropping the restriction.
        """
        if self.organism_group and not self.taxon_ids:
            raise UnsupportedFilterError(
                "REST cannot filter on organism group; provide taxon_ids"
            )
        if self.names:
            raise UnsupportedFilterError("REST needs taxon ids, not names")
        if self.county or self.municipality:
            raise UnsupportedFilterError(
                "REST area filters need area feature ids, not names"
            )

        body: dict = {}
        taxon: dict = {}
        if self.taxon_ids:
            taxon["ids"] = [int(i) for i in self.taxon_ids]
            taxon["includeUnderlyingTaxa"] = True
        if self.redlist_categories:
            taxon["redListCategories"] = list(self.redlist_categories)
        if taxon:
            body["taxon"] = taxon

        if self.date_from or self.date_to:
            date_filter: dict = {"dateFilterType": "OverlappingStartDateAndEndDate"}
            if self.date_from:
                date_filter["startDate"] = self.date_from.isoformat()
            if self.date_to:
                date_filter["endDate"] = self.date_to.isoformat()
            body["date"] = date_filter

        geographics: dict = {}
        if self.bbox_wgs84:
            b = self.bbox_wgs84
            geographics["boundingBox"] = {
                "topLeft": {"latitude": b.north, "longitude": b.west},
                "bottomRight": {"latitude": b.south, "longitude": b.east},
            }
        if self.polygon_wgs84:
            geographics["geometries"] = [self.polygon_wgs84]
        if self.max_uncertainty_m is not None:
            geographics["maxAccuracy"] = int(self.max_uncertainty_m)
        if geographics:
            body["geographics"] = geographics

        body["occurrenceStatus"] = _OCCURRENCE_REST[self.occurrence]
        if self.dataset_ids:
            body["dataProvider"] = {"ids": [int(i) for i in self.dataset_ids]}
        body["verificationStatus"] = (
            "Verified" if self.verified_only else "BothVerifiedAndNotVerified"
        )
        if self.exclude_uncertain_identification:
            body["determinationFilter"] = "NotUnsureDetermination"
        return body


def _prop(field: str) -> str:
    return f"<ogc:PropertyName>{field}</ogc:PropertyName>"


def _lit(value) -> str:
    return f"<ogc:Literal>{escape(str(value))}</ogc:Literal>"


def _eq(field: str, value) -> str:
    return f"<ogc:PropertyIsEqualTo>{_prop(field)}{_lit(value)}</ogc:PropertyIsEqualTo>"


def _cmp(operator: str, field: str, value) -> str:
    return f"<ogc:{operator}>{_prop(field)}{_lit(value)}</ogc:{operator}>"


def _like(field: str, value: str) -> str:
    """Case-insensitive exact match: wildcard characters in ``value`` are escaped."""
    for char in ("\\", "*", "?"):
        value = value.replace(char, "\\" + char)
    return (
        '<ogc:PropertyIsLike wildCard="*" singleChar="?" escapeChar="\\" matchCase="false">'
        f"{_prop(field)}{_lit(value)}</ogc:PropertyIsLike>"
    )


def _or(terms: list) -> str:
    return terms[0] if len(terms) == 1 else "<ogc:Or>" + "".join(terms) + "</ogc:Or>"


def _bbox(b: BoundingBoxWgs84) -> str:
    # GML 2 Box, WGS84 in longitude,latitude order (verified against the service).
    return (
        f"<ogc:BBOX>{_prop(_GEOMETRY_FIELD)}"
        '<gml:Box srsName="EPSG:4326">'
        f"<gml:coordinates>{b.west},{b.south} {b.east},{b.north}</gml:coordinates>"
        "</gml:Box></ogc:BBOX>"
    )


def _ring(coords) -> str:
    pts = " ".join(f"{x},{y}" for x, y in coords)
    return f"<gml:LinearRing><gml:coordinates>{pts}</gml:coordinates></gml:LinearRing>"


def _intersects(geometry: dict) -> str:
    if geometry.get("type") != "Polygon":
        raise UnsupportedFilterError("only GeoJSON Polygon is supported")
    outer, *holes = geometry["coordinates"]
    polygon = f"<gml:outerBoundaryIs>{_ring(outer)}</gml:outerBoundaryIs>"
    polygon += "".join(f"<gml:innerBoundaryIs>{_ring(h)}</gml:innerBoundaryIs>" for h in holes)
    return (
        f"<ogc:Intersects>{_prop(_GEOMETRY_FIELD)}"
        f'<gml:Polygon srsName="EPSG:4326">{polygon}</gml:Polygon></ogc:Intersects>'
    )


# -- Count assessment ----------------------------------------------------------

OK = "ok"
WARN = "warn"
CAPPED = "capped"


@dataclass(frozen=True)
class CountAssessment:
    status: str  # OK, WARN or CAPPED
    count: int
    at_least: bool  # True when ``count`` is only a lower bound


def assess_count(
    count: int, warn_at: int = WARN_THRESHOLD, cap: int = WFS_PAGING_LIMIT
) -> CountAssessment:
    """Classify a match count. A count at the paging limit is only a lower bound."""
    if count >= cap:
        return CountAssessment(CAPPED, count, at_least=True)
    if count >= warn_at:
        return CountAssessment(WARN, count, at_least=False)
    return CountAssessment(OK, count, at_least=False)
