"""Snapshot download logic tests. No network."""
import json

import pytest

from species_data.counting import CancelledError
from species_data.query import Query
from species_data.snapshot import CORE_FIELDS, EXTRA_FIELDS, Row, collect, fields_for, parse_page
from species_data.wfs import request_params

NAMES = tuple(n for n, _ in CORE_FIELDS)


def make_row(i):
    return Row({**dict.fromkeys(NAMES), "occurrenceId": f"id{i}"}, float(i), 6000000.0)


def fake_fetch(total_available, calls=None):
    def fetch(start, size):
        if calls is not None:
            calls.append((start, size))
        return [make_row(i) for i in range(start, min(start + size, total_available))]

    return fetch


def test_parse_page_keeps_known_fields_only_and_skips_missing_geometry():
    page = {
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                "properties": {"occurrenceId": "a", "recordedBy": "Someone", "county": "Skåne"},
            },
            {"geometry": None, "properties": {"occurrenceId": "b"}},
        ]
    }
    rows = parse_page(json.dumps(page), ("occurrenceId", "county"))
    assert len(rows) == 1
    assert (rows[0].x, rows[0].y) == (1.0, 2.0)
    assert rows[0].properties["county"] == "Skåne"
    assert "recordedBy" not in rows[0].properties


def test_collect_pages_through_all_rows():
    calls = []
    rows = collect(fake_fetch(2500, calls), total=2500, page_size=1000)
    assert len(rows) == 2500
    assert calls == [(0, 1000), (1000, 1000), (2000, 1000)]


def test_collect_stops_on_short_page():
    calls = []
    rows = collect(fake_fetch(1200, calls), total=5000, page_size=1000)
    assert len(rows) == 1200
    assert len(calls) == 2


def test_collect_removes_duplicates_from_shifting_data():
    def fetch(start, size):
        first = max(start - 3, 0)
        return [make_row(i) for i in range(first, first + size)]

    assert len(collect(fetch, total=2000, page_size=1000)) == 1997


def test_collect_reports_progress_and_can_be_cancelled():
    progress = []
    collect(fake_fetch(2000), 2000, 1000, on_progress=lambda done, total: progress.append(done))
    assert progress == [1000, 2000]
    state = {"pages": 0}

    def fetch(start, size):
        state["pages"] += 1
        return fake_fetch(5000)(start, size)

    with pytest.raises(CancelledError):
        collect(fetch, 5000, 1000, is_cancelled=lambda: state["pages"] >= 2)
    assert state["pages"] == 2


def test_request_params_ask_only_for_listed_fields_plus_geometry():
    params = request_params(Query(), 2000, 1000, fields=NAMES)
    names = params["propertyName"].split(",")
    assert names[-1] == "point"
    assert "recordedBy" not in names and "reportedBy" not in names
    assert params["maxFeatures"] == "1000" and params["startIndex"] == "2000"


def test_no_personal_fields_are_requested():
    from species_data.wfs import PERSONAL_FIELDS

    every = {n for n, _ in CORE_FIELDS} | {n for g in EXTRA_FIELDS.values() for n, _ in g}
    assert not set(PERSONAL_FIELDS) & every


def test_fields_for_adds_conditional_and_extra_fields():
    names = lambda fields: [n for n, _ in fields]  # noqa: E731
    base = names(fields_for(Query(exclude_uncertain_identification=True)))
    assert base == [n for n, _ in CORE_FIELDS]
    assert "county" in base and "province" in base
    both = names(fields_for(Query(occurrence="both", exclude_uncertain_identification=False)))
    assert "isNeverFoundObservation" in both and "isUncertainIdentification" in both
    extra = names(fields_for(Query(exclude_uncertain_identification=True), ("habitat", "quantity")))
    assert extra[-3:] == ["habitat", "organismQuantity", "organismQuantityUnit"]
    assert "occurrenceRemarks" not in base


def test_year_colours_are_stable_and_differ_between_neighbouring_years():
    from species_data.styles import year_color_hsv

    assert year_color_hsv(2026) == year_color_hsv(2026)
    hues = [year_color_hsv(y)[0] for y in range(2015, 2027)]
    assert len(set(round(h, 3) for h in hues)) == len(hues)
    assert all(0 <= h < 1 for h in hues)
    gaps = [abs(hues[i] - hues[i + 1]) for i in range(len(hues) - 1)]
    assert min(min(g, 1 - g) for g in gaps) > 0.1
