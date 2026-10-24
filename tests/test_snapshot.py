"""Snapshot download logic tests. No network."""
import json

import pytest

from species_data.query import Query
from species_data.snapshot import FIELD_NAMES, CancelledError, Row, collect, parse_page
from species_data.wfs import request_params


def make_row(i):
    return Row({**dict.fromkeys(FIELD_NAMES), "occurrenceId": f"id{i}"}, float(i), 6000000.0)


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
    rows = parse_page(json.dumps(page))
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
    params = request_params(Query(), 2000, 1000, fields=FIELD_NAMES)
    names = params["propertyName"].split(",")
    assert names[-1] == "point"
    assert "recordedBy" not in names and "reportedBy" not in names
    assert params["maxFeatures"] == "1000" and params["startIndex"] == "2000"


def test_no_personal_fields_are_requested():
    from species_data.wfs import PERSONAL_FIELDS

    assert not set(PERSONAL_FIELDS) & set(FIELD_NAMES)
