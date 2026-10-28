"""Standard settings and stored settings of the Localities and Co-occurrence tabs (no QGIS imports).

Most users only want to say how large a locality should be, so three sizes are offered and
the individual distances (link distance, the limit for vague observations, the largest
radius) follow from the size. The individual values stay available under "Advanced".

The settings of a run are also stored in the metadata of the result layer as JSON, so a
result can be repeated exactly, and the tabs remember the values of the last run.
"""
import json
from dataclasses import asdict, fields

# (key, locality size in metres). A locality is at most this wide (radius), observations within
# this distance of each other link, and vaguer observations join one locality only.
SIZE_PRESETS = (("strict", 50), ("standard", 100), ("generous", 200))
DEFAULT_SIZE = "standard"
CUSTOM = "custom"

# Keyword vocabularies in the layer metadata that hold the JSON of the settings.
LOCALITIES_KEY = "species_data:localities"
PLACES_KEY = "species_data:places"
FORMAT_VERSION = 1


def size_of(name: str) -> int:
    return dict(SIZE_PRESETS)[name]


def locality_values(size: float) -> dict:
    """The locality settings that follow from a size."""
    return {"link_distance": size, "bridge_uncertainty": size, "max_radius": size}


def place_values(size: float) -> dict:
    """The co-occurrence settings that follow from a locality size.

    Localities of different species belong to the same place when they are within one and a
    half times the size of each other (plus their radii), and a place is at most three times
    the size, which for the standard size gives 150 m and 300 m.
    """
    return {"max_gap": 1.5 * size, "max_radius": 3 * size}


def preset_name(values: dict, make_values) -> str:
    """The name of the size preset the values match, or ``CUSTOM``."""
    for name, size in SIZE_PRESETS:
        wanted = make_values(size)
        if all(abs(values.get(key, -1) - wanted[key]) < 1e-9 for key in wanted):
            return name
    return CUSTOM


def dumps(params) -> str:
    """The settings (a dataclass) as JSON text for the layer metadata."""
    return json.dumps({"version": FORMAT_VERSION, **asdict(params)}, sort_keys=True)


def loads(text: str, cls):
    """Settings of class ``cls`` from JSON text, or None when the text is not usable.

    Missing keys keep their default, unknown keys are ignored, and values are converted to
    the type of the default so a hand edited text cannot put a string in a number.
    """
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    defaults = cls()
    values = {}
    for field in fields(cls):
        if field.name not in data:
            continue
        default = getattr(defaults, field.name)
        try:
            values[field.name] = type(default)(data[field.name])
        except (TypeError, ValueError):
            return None
    return cls(**values)
