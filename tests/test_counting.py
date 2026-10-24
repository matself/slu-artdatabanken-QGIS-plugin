"""Counting probe tests. No network."""
import pytest

from species_data.counting import Count, at_least, count
from species_data.query import Query
from species_data.wfs import layer_uri, request_params


def probe_for(total):
    calls = []

    def exists(index):
        calls.append(index)
        return index < total

    return exists, calls


@pytest.mark.parametrize("total", [0, 1, 2, 3, 5, 100, 1999, 2000, 4097, 15978, 99999])
def test_exact_count(total):
    exists, calls = probe_for(total)
    assert count(exists) == Count(total, True)
    assert len(calls) <= 40


def test_limit_is_a_lower_bound():
    exists, _ = probe_for(10**7)
    assert count(exists) == Count(100000, False)


def test_custom_limit():
    exists, _ = probe_for(500)
    assert count(exists, limit=100) == Count(100, False)
    exists, _ = probe_for(50)
    assert count(exists, limit=100) == Count(50, True)


def test_at_least_uses_one_request():
    exists, calls = probe_for(2000)
    assert at_least(exists, 2000)
    assert calls == [1999]
    exists, _ = probe_for(1999)
    assert not at_least(exists, 2000)


def test_request_params_include_filter_and_paging():
    params = request_params(Query(county="Skåne"), start_index=1999)
    assert params["startIndex"] == "1999"
    assert params["version"] == "1.0.0"
    assert "Skåne" in params["filter"]


def test_layer_uri_escapes_quotes():
    uri = layer_uri(Query(municipality="O'Brien"))
    assert uri.startswith("url='https://sosgeo.artdata.slu.se/geoserver/SOS/ows'")
    assert "pagingEnabled='true'" in uri
    assert "O\'Brien" in uri
    assert "version='1.0.0'" in uri


def test_provenance_mentions_source_and_disclaimer():
    from datetime import datetime

    from species_data import provenance

    text = provenance.abstract(Query(county="Skåne"), Count(346, True), datetime(2026, 10, 24))
    assert "SLU Artdatabanken" in text
    assert "2026-10-24" in text
    assert "County: Skåne" in text
    assert "not developed, owned or endorsed by SLU" in text
    assert "at least" in provenance.abstract(Query(), Count(100000, False), datetime(2026, 1, 1))
