"""Reading an export from Fynddata. No QGIS needed. The data here is made up."""
import json

from species_data import fynddata_export as export
from species_data import provenance, source_check


def feature(**columns):
    properties = {
        "Observation GUID": "urn:test:1",
        "Vetenskapligt namn": "Pulsatilla vulgaris",
        "Svenskt namn": "backsippa",
        "Startdatum": "2020-06-21",
        "Slutdatum": "2020-06-21",
        "Koordinatnoggrannhet (m)": 25,
        "Dataset namn": "Artportalen",
        "Ej funnen": False,
        "Ej återfunnen": False,
        "Osäker artbestämning": False,
        "Observatör": "A Person",
    }
    properties.update(columns)
    return {"type": "Feature", "properties": properties, "geometry": {"type": "Point", "coordinates": [14.3, 55.6]}}


def identity(lon, lat):
    return lon * 10, lat * 10


def test_an_export_is_recognised_by_its_columns():
    mapping = export.match_columns(export.columns_of([feature()]))
    assert mapping.language == "sv"
    assert mapping.missing == ()
    assert mapping.columns["scientificName"] == "Vetenskapligt namn"


def test_missing_required_columns_are_named():
    names = export.columns_of([feature()]) - {"Slutdatum", "Koordinatnoggrannhet (m)"}
    mapping = export.match_columns(names)
    assert set(mapping.missing) == {"endDate", "coordinateUncertaintyInMeters"}


def test_something_that_is_not_an_export_is_not_matched():
    assert export.match_columns({"id", "name", "geom"}) is None


def test_only_the_fields_of_the_layer_are_read_never_the_observer():
    mapping = export.match_columns(export.columns_of([feature()]))
    rows = export.build_rows([feature()], mapping, identity)
    assert set(rows[0].properties) == {name for name, _ in export.FIELDS}
    assert "A Person" not in rows[0].properties.values()


def test_a_row_has_the_values_and_the_transformed_position():
    mapping = export.match_columns(export.columns_of([feature()]))
    row = export.build_rows([feature()], mapping, identity)[0]
    assert (row.x, row.y) == (143.0, 556.0)
    assert row.properties["scientificName"] == "Pulsatilla vulgaris"
    assert row.properties["endDate"] == "2020-06-21"
    assert row.properties["coordinateUncertaintyInMeters"] == 25
    assert row.properties["isPresentObservation"] is True


def test_absence_is_left_out_but_not_refound_is_kept():
    mapping = export.match_columns(export.columns_of([feature()]))
    absent = feature(**{"Ej funnen": True})
    not_refound = feature(**{"Ej funnen": True, "Ej återfunnen": True})
    rows = export.build_rows([feature(), absent, not_refound], mapping, identity)
    assert len(rows) == 2
    assert rows[1].properties["isNotRediscoveredObservation"] is True


def test_features_without_a_point_are_skipped():
    mapping = export.match_columns(export.columns_of([feature()]))
    broken = feature()
    broken["geometry"] = None
    assert export.build_rows([broken], mapping, identity) == []


def test_the_layer_fields_pass_the_source_check_of_the_other_tabs():
    names = [name for name, _ in export.FIELDS]
    problems = source_check.problems(names, export.abstract("x.geojson", 1, export.Sidecars(), "2026-11-05"), True, 1)
    assert problems == []


def test_the_abstract_names_the_source_and_the_filter_when_it_is_known():
    sidecars = export.Sidecars(filter_text="# Filter 2026-11-05 15:33 #\nPresent", datasets=(("Artportalen", 5),))
    text = export.abstract("x.geojson", 5, sidecars, "2026-11-05")
    assert provenance.SOURCE in text
    assert "Present" in text and "Artportalen (5)" in text
    assert "was not read" in export.abstract("x.geojson", 5, export.Sidecars(), "2026-11-05")


def write_export_files(folder, stamp="2026-11-05 15:33", other_stamp=None):
    file = folder / f"Observations {stamp.replace(':', '.')} SOS export.geojson"
    file.write_text(json.dumps({"type": "FeatureCollection", "features": [feature()]}), encoding="utf-8")
    heading = other_stamp or stamp
    (folder / "filter.md").write_text(f"# Filter {heading} #\nPresent", encoding="utf-8")
    (folder / "citation.md").write_text(f"# Citeringsanvisning {heading} #\nCite this", encoding="utf-8")
    (folder / "datasets.md").write_text(
        f"# Datasets {heading} #\n\n| Dataset | Antal observationer | Publika observationer | I denna fil |\n"
        "| ---------- | ---------- | ---------- | ---------- |\n"
        "| Artportalen | 100 | 90 | 5 |\n| Biologg | 50 | 50 | 0 |\n",
        encoding="utf-8",
    )
    return file


def test_the_files_next_to_the_export_are_read_when_the_time_matches(tmp_path):
    sidecars = export.read_sidecars(write_export_files(tmp_path))
    assert "Present" in sidecars.filter_text
    assert "Cite this" in sidecars.citation_text
    assert sidecars.datasets == (("Artportalen", 5),)  # only datasets that have observations in the file
    assert sidecars.other_exports == ()


def test_files_of_another_export_are_not_used_but_reported(tmp_path):
    sidecars = export.read_sidecars(write_export_files(tmp_path, other_stamp="2026-01-01 08:00"))
    assert sidecars.filter_text == "" and sidecars.citation_text == "" and sidecars.datasets == ()
    assert set(sidecars.other_exports) == {"filter.md", "citation.md", "datasets.md"}


def test_a_renamed_export_gets_no_files_because_they_cannot_be_checked(tmp_path):
    file = write_export_files(tmp_path)
    renamed = file.rename(tmp_path / "mine.geojson")
    sidecars = export.read_sidecars(renamed)
    assert sidecars.filter_text == ""
    assert "filter.md" in sidecars.other_exports


def test_the_layer_is_named_after_the_time_of_the_export():
    name = export.layer_name("Observations 2026-11-05 15.33 SOS export.geojson", 5988)
    assert name == "Fynddata 2026-11-05 15.33 (5988)"
    assert export.layer_name("mine.geojson", 3) == "mine (3)"


def test_features_are_read_from_a_geojson_file(tmp_path):
    file = write_export_files(tmp_path)
    assert len(export.read_features(file)) == 1
