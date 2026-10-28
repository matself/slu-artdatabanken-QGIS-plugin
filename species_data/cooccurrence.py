"""Find the places where several species have been reported from the same place (no QGIS imports).

The input is the localities of each species, as made by ``clustering.py``. Localities of
different species belong to the same place when the distance between their centres is at
most the chosen gap plus their two radii. The linking and the limit on the size of a place
are the ones of ``clustering.cluster``, applied to the localities instead of to
observations, so a string of localities along a shore is split in the same way.
"""
import math
from dataclasses import dataclass, field
from typing import Optional

from . import clustering

# The radius of a place holds this share of its observations (the rest are outliers).
CORE_SHARE = 0.9
CURRENT_CATEGORIES = (clustering.STRONG, clustering.SPORADIC)


@dataclass(frozen=True)
class Node:
    species: str
    x: float
    y: float
    radius: float  # metres from the centre to the furthest observation
    observations: int
    not_refound: int  # how many of the observations say "searched for, not found"
    category: str
    first_year: Optional[int] = None
    last_year: Optional[int] = None


@dataclass(frozen=True)
class Params:
    max_gap: float = 150.0  # metres between two localities that still belong together
    max_radius: float = 300.0  # metres. Wider places are split up, 0 = no limit
    only_current: bool = False  # leave out localities without recent records
    count_not_refound: bool = False  # let "searched for, not found" count as present


@dataclass
class Place:
    id: int
    x: float
    y: float
    radius: float  # metres from (x, y) that hold CORE_SHARE of the observations
    members: list  # indexes into the input nodes
    species: tuple  # the species found here, sorted
    localities: dict  # species -> number of localities of that species here
    first_year: Optional[int]
    last_year: Optional[int]
    all_species: bool


@dataclass
class Result:
    places: list = field(default_factory=list)
    wanted: tuple = ()
    left_out: int = 0  # localities that were not considered


def eligible(node: Node, params: Params) -> bool:
    """Does the locality count as a place where its species occurs?"""
    if not params.count_not_refound and node.observations <= node.not_refound:
        return False
    if params.only_current and node.category not in CURRENT_CATEGORIES:
        return False
    return True


def find_places(nodes: list, wanted: tuple, params: Params = Params()) -> Result:
    """Group the localities of the ``wanted`` species into places."""
    wanted = tuple(sorted(wanted))
    usable = [i for i, n in enumerate(nodes) if n.species in wanted and eligible(n, params)]
    result = Result(wanted=wanted, left_out=len(nodes) - len(usable))
    # Each locality is a point whose uncertainty is its radius, so large localities reach further.
    points = [clustering.Point(nodes[i].x, nodes[i].y, None, nodes[i].radius) for i in usable]
    # Every locality may link and none is left out: the limits are just above the widest locality.
    # They also set the cell size of the search grid, so they must not be larger than needed.
    widest = max((p.uncertainty for p in points), default=0.0) + 1.0
    grouping = clustering.cluster(
        points,
        clustering.Params(
            link_distance=params.max_gap,
            uncertainty_weight=1.0,
            max_uncertainty=widest,
            bridge_uncertainty=widest,
            max_radius=params.max_radius,
        ),
    )
    for locality in grouping.localities:
        members = [usable[m] for m in locality.members]
        counts = {}
        for i in members:
            counts[nodes[i].species] = counts.get(nodes[i].species, 0) + 1
        found = tuple(sorted(counts))
        firsts = [nodes[i].first_year for i in members if nodes[i].first_year]
        lasts = [nodes[i].last_year for i in members if nodes[i].last_year]
        x, y, radius = _centre_and_radius([nodes[i] for i in members])
        result.places.append(
            Place(
                id=locality.id,
                x=x,
                y=y,
                radius=radius,
                members=members,
                species=found,
                localities=counts,
                first_year=min(firsts) if firsts else None,
                last_year=max(lasts) if lasts else None,
                all_species=set(wanted) <= set(found),
            )
        )
    return result


def _centre_and_radius(members: list) -> tuple:
    """Centre and radius of a place from where the observations are.

    The centre is the mean of the locality centres weighted by their number of observations.
    The radius is the distance from it that holds ``CORE_SHARE`` of the observations, so a few
    outlying localities do not stretch it.
    """
    weights = [max(n.observations, 1) for n in members]
    total = sum(weights)
    x = sum(n.x * w for n, w in zip(members, weights)) / total
    y = sum(n.y * w for n, w in zip(members, weights)) / total
    by_distance = sorted((math.hypot(n.x - x, n.y - y), w) for n, w in zip(members, weights))
    reached = 0
    for distance, weight in by_distance:
        reached += weight
        if reached >= CORE_SHARE * total:
            return x, y, distance
    return x, y, by_distance[-1][0]
