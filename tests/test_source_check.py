"""Source check tests. No QGIS needed."""
from species_data import provenance
from species_data.source_check import REQUIRED_FIELDS, problems

GOOD = provenance.citation(__import__("datetime").datetime(2026, 10, 28))


def test_plugin_layer_is_accepted():
    assert problems(REQUIRED_FIELDS, GOOD, True, 10) == []


def test_other_layers_are_rejected_with_reasons():
    found = problems(("name",), "", False, 0)
    assert [code for code, _ in found] == ["not_point", "missing_fields", "no_source", "empty"]


def test_missing_metadata_alone_is_reported():
    assert problems(REQUIRED_FIELDS, "Some other abstract", True, 3) == [("no_source", "")]
