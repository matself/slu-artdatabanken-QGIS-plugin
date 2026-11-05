"""Names of taxa (no QGIS imports).

The service stores a subspecies under its own scientific name (``Pulsatilla vulgaris subsp.
vulgaris``), so a species is spread over several names. Localities are formed per species, so
the names below a species are folded into it.
"""
import re

# The rank marker and everything after it, for the infraspecific ranks of plants.
_BELOW_SPECIES = re.compile(
    r"\s+(?:subsp|ssp|var|subvar|f|subf|forma|nothosubsp|nothovar)\.?(?:\s.*)?$", re.IGNORECASE
)
_HYBRID_SIGNS = ("\u00d7", " x ")


def summary(names: list) -> str:
    """The names and how many observations carry each, most frequent first, for example
    ``Pulsatilla vulgaris (12); Pulsatilla vulgaris subsp. vulgaris (30)``.

    Used for the scientific names and for the data sources of the observations in a locality.
    """
    counts = {}
    for name in names:
        counts[name] = counts.get(name, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return "; ".join(f"{name} ({n})" for name, n in ordered)


def species_name(scientific_name: str) -> str:
    """The species of a scientific name: ``Pulsatilla vulgaris subsp. vulgaris`` gives
    ``Pulsatilla vulgaris``.

    Names that are not below a species are returned as they are. Hybrids are kept whole,
    because a hybrid formula such as ``Pulsatilla pratensis x vulgaris`` is not a subspecies of
    either parent.
    """
    name = " ".join(scientific_name.split())
    if any(sign in name for sign in _HYBRID_SIGNS):
        return name
    return _BELOW_SPECIES.sub("", name)
