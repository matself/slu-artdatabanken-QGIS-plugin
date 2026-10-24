"""Colour choices for the observation layer (no QGIS imports)."""

# Consecutive years are about 137.5 degrees apart on the colour wheel (the golden angle),
# so neighbouring years get clearly different, pseudo-random looking colours. The colour of
# a year is the same in every layer, which makes layers from different searches comparable.
GOLDEN_ANGLE = 137.508
SATURATION = 0.75
VALUE = 0.85
NO_DATE_COLOR = "#999999"


def year_color_hsv(year: int) -> tuple:
    """(hue 0-1, saturation, value) for a year."""
    return ((year * GOLDEN_ANGLE) % 360) / 360, SATURATION, VALUE
