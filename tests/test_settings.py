"""Settings tests. No QGIS needed."""
from species_data import clustering, cooccurrence, settings


def test_standard_size_gives_the_standard_values():
    assert settings.size_of("standard") == 100
    assert settings.locality_values(100) == {"link_distance": 100, "bridge_uncertainty": 100, "max_radius": 100}
    assert settings.place_values(100) == {"max_gap": 150.0, "max_radius": 300}


def test_the_defaults_of_the_tabs_are_the_standard_size():
    p = clustering.Params()
    assert settings.preset_name(
        {"link_distance": p.link_distance, "bridge_uncertainty": p.bridge_uncertainty, "max_radius": p.max_radius},
        settings.locality_values,
    ) == settings.DEFAULT_SIZE
    q = cooccurrence.Params()
    assert settings.preset_name({"max_gap": q.max_gap, "max_radius": q.max_radius}, settings.place_values) == "standard"


def test_preset_name_is_custom_when_values_differ():
    values = settings.locality_values(100) | {"max_radius": 120}
    assert settings.preset_name(values, settings.locality_values) == settings.CUSTOM
    assert settings.preset_name(settings.locality_values(50), settings.locality_values) == "strict"


def test_settings_round_trip_through_json():
    params = clustering.Params(link_distance=50, uncertainty_weight=0.0, max_radius=75, reference_year=2030)
    assert settings.loads(settings.dumps(params), clustering.Params) == params
    places = cooccurrence.Params(max_gap=75, only_current=True)
    assert settings.loads(settings.dumps(places), cooccurrence.Params) == places


def test_loading_is_forgiving_about_missing_and_unknown_keys():
    loaded = settings.loads('{"version": 1, "link_distance": 60, "something_new": 1}', clustering.Params)
    assert loaded.link_distance == 60 and loaded.max_radius == clustering.Params().max_radius


def test_loading_rejects_text_that_is_not_settings():
    assert settings.loads("not json", clustering.Params) is None
    assert settings.loads("[1, 2]", clustering.Params) is None
    assert settings.loads('{"link_distance": "far"}', clustering.Params) is None
    assert settings.loads(None, clustering.Params) is None
