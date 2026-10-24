"""Query model tests. No QGIS or network needed."""
import xml.etree.ElementTree as ET
from datetime import date

import pytest

from species_data.query import (
    ABSENT,
    BOTH,
    CAPPED,
    OK,
    WARN,
    BoundingBoxWgs84,
    Query,
    UnsupportedFilterError,
    assess_count,
)

OGC = "{http://www.opengis.net/ogc}"
GML = "{http://www.opengis.net/gml}"


def parse(query):
    return ET.fromstring(query.to_ogc_filter())


def conditions(root):
    """(operator, property, literal) for every comparison in the filter."""
    found = []
    for el in root.iter():
        name = el.tag.replace(OGC, "")
        if name.startswith("PropertyIs"):
            found.append((name, el.find(OGC + "PropertyName").text, el.find(OGC + "Literal").text))
    return found


def test_default_is_vascular_plants_present_only():
    root = parse(Query())
    assert root.find(OGC + "And") is not None
    assert conditions(root) == [
        ("PropertyIsEqualTo", "organismGroup", "Kärlväxter"),
        ("PropertyIsEqualTo", "isPresentObservation", "true"),
    ]


def test_empty_query_has_no_filter():
    assert Query(organism_group=None, occurrence=BOTH).to_ogc_filter() == ""


def test_single_term_is_not_wrapped_in_and():
    root = parse(Query(organism_group=None, occurrence=BOTH, county="Skåne"))
    assert root.find(OGC + "And") is None
    assert conditions(root) == [("PropertyIsEqualTo", "county", "Skåne")]


def test_special_characters_are_escaped():
    q = Query(organism_group=None, occurrence=BOTH, county="A<&>B")
    assert "A&lt;&amp;&gt;B" in q.to_ogc_filter()
    assert conditions(parse(q))[0][2] == "A<&>B"


def like_terms(query):
    """(property, literal, matchCase) of every PropertyIsLike in the filter."""
    root = parse(query)
    return [
        (e.find(OGC + "PropertyName").text, e.find(OGC + "Literal").text, e.get("matchCase"))
        for e in root.iter(OGC + "PropertyIsLike")
    ]


def names_query(*names):
    return Query(organism_group=None, occurrence=BOTH, names=names)


def test_species_and_swedish_names_match_exactly_ignoring_case():
    likes = like_terms(names_query("Primula veris", "gullviva"))
    assert [(f, v) for f, v, _ in likes if v == "Primula veris"] == [
        ("scientificName", "Primula veris"),
        ("vernacularName", "Primula veris"),
    ]
    assert ("vernacularName", "gullviva", "false") in likes
    assert all(case == "false" for _, _, case in likes)
    assert parse(names_query("a", "b")).find(OGC + "Or") is not None


def test_a_genus_name_means_the_genus_and_every_species_in_it():
    likes = like_terms(names_query("Anemone"))
    assert ("scientificName", "Anemone", "false") in likes
    assert ("scientificName", "Anemone *", "false") in likes
    assert like_terms(names_query("Anemone spp.")) == [
        ("scientificName", "Anemone", "false"),
        ("scientificName", "Anemone *", "false"),
    ]


def test_sp_means_observations_identified_to_genus_only():
    assert like_terms(names_query("Anemone sp.")) == [("scientificName", "Anemone", "false")]
    assert like_terms(names_query("anemone SP")) == [("scientificName", "anemone", "false")]


def test_star_is_a_wildcard_and_other_special_characters_are_escaped():
    likes = like_terms(names_query("anem*"))
    assert likes == [("scientificName", "anem*", "false"), ("vernacularName", "anem*", "false")]
    literal = [v for f, v, _ in like_terms(names_query("a?b")) if f == "scientificName"][0]
    assert literal == r"a\?b"


def test_wildcard_in_a_species_name_is_not_expanded_to_genus_terms():
    assert len(like_terms(names_query("Anemone nemorosa"))) == 2


def test_taxon_ids_become_or_of_equals():
    q = Query(organism_group=None, occurrence=BOTH, taxon_ids=(100, 200))
    assert conditions(parse(q)) == [
        ("PropertyIsEqualTo", "dyntaxaTaxonId", "100"),
        ("PropertyIsEqualTo", "dyntaxaTaxonId", "200"),
    ]


def test_bbox_is_in_the_same_filter_as_the_other_terms():
    q = Query(bbox_wgs84=BoundingBoxWgs84(west=13.1, south=55.65, east=13.3, north=55.75))
    root = parse(q)
    box = root.find(f".//{OGC}BBOX")
    assert box.find(OGC + "PropertyName").text == "point"
    coords = box.find(f"{GML}Box/{GML}coordinates")
    assert coords.text == "13.1,55.65 13.3,55.75"
    assert ("PropertyIsEqualTo", "organismGroup", "Kärlväxter") in conditions(root)


def test_polygon_with_hole():
    ring = [[0, 0], [1, 0], [1, 1], [0, 0]]
    hole = [[0.2, 0.2], [0.4, 0.2], [0.4, 0.4], [0.2, 0.2]]
    q = Query(
        organism_group=None,
        occurrence=BOTH,
        polygon_wgs84={"type": "Polygon", "coordinates": [ring, hole]},
    )
    root = parse(q)
    assert root.find(f".//{GML}outerBoundaryIs//{GML}coordinates").text == "0,0 1,0 1,1 0,0"
    inner = root.find(f".//{GML}innerBoundaryIs//{GML}coordinates").text
    assert inner == "0.2,0.2 0.4,0.2 0.4,0.4 0.2,0.2"


def test_multipolygon_is_rejected():
    q = Query(polygon_wgs84={"type": "MultiPolygon", "coordinates": []})
    with pytest.raises(UnsupportedFilterError):
        q.to_ogc_filter()


def test_date_range_keeps_whole_local_days():
    q = Query(
        organism_group=None,
        occurrence=BOTH,
        date_from=date(2020, 1, 1),
        date_to=date(2020, 12, 31),
    )
    assert conditions(parse(q)) == [
        ("PropertyIsGreaterThanOrEqualTo", "endDate", "2020-01-01T00:00:00Z"),
        ("PropertyIsLessThanOrEqualTo", "startDate", "2020-12-31T21:00:00Z"),
    ]


def test_flags_and_uncertainty():
    q = Query(
        organism_group=None,
        occurrence=BOTH,
        verified_only=True,
        redlist_categories=("CR", "NE"),
        exclude_uncertain_identification=True,
        max_uncertainty_m=50,
    )
    assert conditions(parse(q)) == [
        ("PropertyIsEqualTo", "isVerified", "true"),
        ("PropertyIsEqualTo", "redlistCategory", "CR"),
        ("PropertyIsEqualTo", "redlistCategory", "NE"),
        ("PropertyIsEqualTo", "isUncertainIdentification", "false"),
        ("PropertyIsLessThanOrEqualTo", "coordinateUncertaintyInMeters", "50"),
    ]


def test_rest_filter_rejects_names():
    with pytest.raises(UnsupportedFilterError):
        Query(organism_group=None, names=("vitsippa",)).to_sos_filter()


def test_rest_filter_requires_taxon_ids_for_group():
    with pytest.raises(UnsupportedFilterError):
        Query().to_sos_filter()


def test_rest_filter_rejects_area_names():
    with pytest.raises(UnsupportedFilterError):
        Query(organism_group=None, taxon_ids=(1,), county="Skåne").to_sos_filter()


def test_rest_filter_full():
    q = Query(
        organism_group=None,
        taxon_ids=(100,),
        bbox_wgs84=BoundingBoxWgs84(west=12.0, south=55.0, east=14.0, north=56.0),
        date_from=date(2020, 1, 1),
        verified_only=True,
        exclude_uncertain_identification=True,
        max_uncertainty_m=100,
        dataset_ids=(1, 19),
        redlist_categories=("CR", "NE"),
    )
    assert q.to_sos_filter() == {
        "taxon": {
            "ids": [100],
            "includeUnderlyingTaxa": True,
            "redListCategories": ["CR", "NE"],
        },
        "date": {
            "dateFilterType": "OverlappingStartDateAndEndDate",
            "startDate": "2020-01-01",
        },
        "geographics": {
            "boundingBox": {
                "topLeft": {"latitude": 56.0, "longitude": 12.0},
                "bottomRight": {"latitude": 55.0, "longitude": 14.0},
            },
            "maxAccuracy": 100,
        },
        "occurrenceStatus": "Present",
        "dataProvider": {"ids": [1, 19]},
        "verificationStatus": "Verified",
        "determinationFilter": "NotUnsureDetermination",
    }


@pytest.mark.parametrize(
    "count,status,at_least",
    [
        (0, OK, False),
        (1999, OK, False),
        (2000, WARN, False),
        (4999, WARN, False),
        (5000, WARN, False),
        (99999, WARN, False),
        (100000, CAPPED, True),
        (250000, CAPPED, True),
    ],
)
def test_assess_count(count, status, at_least):
    result = assess_count(count)
    assert (result.status, result.at_least) == (status, at_least)


def test_absent_and_both_occurrence():
    absent = conditions(parse(Query(organism_group=None, occurrence=ABSENT)))
    assert absent == [("PropertyIsEqualTo", "isPresentObservation", "false")]
    assert Query(organism_group=None, occurrence=BOTH).to_ogc_filter() == ""
    assert Query(organism_group=None, occurrence=BOTH, taxon_ids=(1,)).to_sos_filter()[
        "occurrenceStatus"
    ] == "BothPresentAndAbsent"


def test_datasets_become_or_of_provider_ids():
    q = Query(organism_group=None, occurrence=BOTH, dataset_ids=(1, 19))
    assert conditions(parse(q)) == [
        ("PropertyIsEqualTo", "dataProviderId", "1"),
        ("PropertyIsEqualTo", "dataProviderId", "19"),
    ]
