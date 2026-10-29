"""The method descriptions in docs/ must state the defaults the code uses. No QGIS needed."""
import re
from pathlib import Path

from species_data import clustering, cooccurrence, settings

DOCS = Path(__file__).resolve().parent.parent / "docs"


def _defaults(name):
    text = (DOCS / name).read_text(encoding="utf-8")
    found = re.search(r"<!-- defaults: (.*?) -->", text)
    assert found, f"{name} has no defaults line"
    return dict(item.split("=") for item in found.group(1).split())


def _same(documented, actual):
    return str(documented).lower() == str(actual).lower() or float(documented) == float(actual)


def test_locality_method_states_the_defaults_of_the_code():
    documented = _defaults("metod-lokaler.md")
    p = clustering.Params()
    for key in ("link_distance", "uncertainty_weight", "max_uncertainty", "bridge_uncertainty", "max_radius",
                "recent_years", "historical_years", "strong_min_years"):
        assert _same(documented[key], getattr(p, key)), key
    assert documented["presets"] == ",".join(str(size) for _, size in settings.SIZE_PRESETS)


def test_cooccurrence_method_states_the_defaults_of_the_code():
    documented = _defaults("metod-samvariation.md")
    p = cooccurrence.Params()
    assert _same(documented["max_gap"], p.max_gap)
    assert _same(documented["max_radius"], p.max_radius)
    assert documented["only_current"] == str(p.only_current).lower()
    assert documented["count_not_refound"] == str(p.count_not_refound).lower()
    assert _same(documented["core_share"], cooccurrence.CORE_SHARE)
    values = settings.place_values(100)
    assert _same(documented["place_gap_factor"], values["max_gap"] / 100)
    assert _same(documented["place_radius_factor"], values["max_radius"] / 100)
