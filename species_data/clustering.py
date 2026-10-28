"""Group observations into localities (no QGIS imports).

Frequently reported species are often reported many times per year from the same site,
with different coordinate uncertainty, so one site looks like several points. Observations
are linked into one locality when they are close enough, and the distance that counts as
close grows with the uncertainty of the two observations. Links are transitive (single
linkage), so a chain of observations forms one locality, while localities further apart
than the link distance stay separate. All coordinates are in metres (SWEREF 99 TM).
"""
import math
from dataclasses import dataclass, field
from typing import Optional

# Locality classes. The year limits are parameters, see ``Params``.
STRONG = "Strong current"
SPORADIC = "Sporadic current"
HISTORICAL = "Historical"
NOT_REFOUND = "Not refound"
UNCERTAIN = "Uncertain"


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    year: Optional[int]
    uncertainty: Optional[float] = None  # metres, None when not reported
    not_refound: bool = False  # the observation says the species was searched for but not found


@dataclass(frozen=True)
class Params:
    link_distance: float = 100.0  # metres between two exact points that still link
    uncertainty_weight: float = 1.0  # 0 ignores uncertainty, 1 adds it in full
    max_uncertainty: float = 500.0  # metres. Less precise observations are left out
    bridge_uncertainty: float = 100.0  # metres. Vaguer observations join one locality only
    max_radius: float = 100.0  # metres. Wider localities are split up, 0 = no limit
    reference_year: int = 2026
    recent_years: int = 5  # last observation at most this many years back = current
    historical_years: int = 15  # last observation more than this many years back = historical
    strong_min_years: int = 5  # distinct years with observations needed for "strong"


@dataclass
class Locality:
    id: int
    members: list  # indexes into the input list
    x: float
    y: float
    radius: float  # largest distance from (x, y) to a member
    count: int
    years: list  # sorted distinct years
    first_year: Optional[int]
    last_year: Optional[int]
    category: str
    not_refound_count: int = 0


@dataclass
class Result:
    localities: list = field(default_factory=list)
    left_out: list = field(default_factory=list)  # input indexes above ``max_uncertainty``


def _effective(point: Point, params: Params) -> float:
    """Uncertainty used for linking, capped so a vague point cannot bridge distant sites."""
    u = params.max_uncertainty if point.uncertainty is None else point.uncertainty
    return min(u, params.max_uncertainty) * params.uncertainty_weight


def _uncertainty(point: Point, params: Params) -> float:
    return params.max_uncertainty if point.uncertainty is None else point.uncertainty


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


class _Sets:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def cluster(points: list, params: Params = Params()) -> Result:
    """Group ``points`` into localities according to ``params``."""
    result = Result()
    kept = []
    for index, point in enumerate(points):
        too_vague = point.uncertainty is not None and point.uncertainty > params.max_uncertainty
        if too_vague:
            result.left_out.append(index)
        else:
            kept.append(index)

    effective = {i: _effective(points[i], params) for i in kept}
    # The largest possible link distance sets the cell size of the search grid.
    reach = params.link_distance + 2 * max(effective.values(), default=0.0)
    cell = max(reach, 1.0)
    buckets = {}
    for i in kept:
        buckets.setdefault((math.floor(points[i].x / cell), math.floor(points[i].y / cell)), []).append(i)
    # Precise points can only reach each other over a shorter distance: a finer grid
    # keeps the number of pairs to test small in dense data.
    precise_cell = max(params.link_distance + 2 * min(params.bridge_uncertainty, params.max_uncertainty) * params.uncertainty_weight, 1.0)
    precise_buckets = {}
    for i in kept:
        if _uncertainty(points[i], params) <= params.bridge_uncertainty:
            key = (math.floor(points[i].x / precise_cell), math.floor(points[i].y / precise_cell))
            precise_buckets.setdefault(key, []).append(i)

    sets = _Sets(len(points))
    precise = [i for i in kept if _uncertainty(points[i], params) <= params.bridge_uncertainty]
    vague = sorted(
        (i for i in kept if _uncertainty(points[i], params) > params.bridge_uncertainty),
        key=lambda i: _uncertainty(points[i], params),
    )

    def limit(a, b):
        return params.link_distance + effective[a] + effective[b]

    def neighbours(i, grid=buckets, size=cell):
        cx, cy = math.floor(points[i].x / size), math.floor(points[i].y / size)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                yield from grid.get((cx + dx, cy + dy), ())

    # Precise observations link freely: chains of them form one locality.
    placed = set(precise)
    for a in precise:
        for b in neighbours(a, precise_buckets, precise_cell):
            if b > a and sets.find(a) != sets.find(b) and _distance(points[a], points[b]) <= limit(a, b):
                sets.union(a, b)
    # A vague observation joins the nearest locality it overlaps and never joins two
    # localities together, so it cannot bridge sites that are apart.
    for a in vague:
        near = [
            (_distance(points[a], points[b]), b)
            for b in neighbours(a)
            if b in placed and _distance(points[a], points[b]) <= limit(a, b)
        ]
        if near:
            sets.union(a, min(near)[1])
        placed.add(a)

    groups = {}
    for i in kept:
        groups.setdefault(sets.find(i), []).append(i)
    if params.max_radius > 0:
        groups = {
            key: part
            for number, members in enumerate(groups.values())
            for key, part in _split(number, members, points, params)
        }
    ordered = sorted(groups.values(), key=lambda g: g[0])
    result.localities = [_locality(n + 1, g, points, params) for n, g in enumerate(ordered)]
    return result


def _split(number, members, points, params):
    """Split a chain of linked observations that is wider than ``max_radius``.

    Along a shore or a road the observations form a string, and linking them makes one
    long locality. The most precise observations become centres, each other observation
    goes to the nearest centre, and one that is further than ``max_radius`` from every
    centre becomes a centre itself.
    """
    if len(members) < 2 or _extent_radius(members, points) <= params.max_radius:
        return [((number, 0), members)]
    centres = []  # indexes of the observations that start a part
    parts = {}
    for i in sorted(members, key=lambda m: (_uncertainty(points[m], params), m)):
        nearest = min(
            ((_distance(points[i], points[c]), c) for c in centres), default=(math.inf, None)
        )
        if nearest[0] <= params.max_radius:
            parts[nearest[1]].append(i)
        else:
            centres.append(i)
            parts[i] = [i]
    return [((number, c), sorted(part)) for c, part in parts.items()]


def _extent_radius(members, points):
    cx = sum(points[i].x for i in members) / len(members)
    cy = sum(points[i].y for i in members) / len(members)
    return max(math.hypot(points[i].x - cx, points[i].y - cy) for i in members)


def _locality(number, members, points, params):
    # Weighted by 1/(1+uncertainty) so that exact points pull the centre more than vague ones.
    weights = [1.0 / (1.0 + (points[i].uncertainty or params.max_uncertainty)) for i in members]
    total = sum(weights)
    x = sum(points[i].x * w for i, w in zip(members, weights)) / total
    y = sum(points[i].y * w for i, w in zip(members, weights)) / total
    radius = max(math.hypot(points[i].x - x, points[i].y - y) for i in members)
    years = sorted({points[i].year for i in members if points[i].year is not None})
    refound = [points[i] for i in members if points[i].not_refound]
    return Locality(
        id=number,
        members=members,
        x=x,
        y=y,
        radius=radius,
        count=len(members),
        years=years,
        first_year=years[0] if years else None,
        last_year=years[-1] if years else None,
        category=classify(members, points, params),
        not_refound_count=len(refound),
    )


def classify(members, points, params: Params) -> str:
    """Class of a locality from the years of its observations."""
    present = [points[i].year for i in members if not points[i].not_refound and points[i].year]
    missing = [points[i].year for i in members if points[i].not_refound and points[i].year]
    last_present = max(present) if present else None
    age = params.reference_year - last_present if last_present else None

    if missing and (last_present is None or max(missing) >= last_present):
        if params.reference_year - max(missing) <= params.historical_years:
            return NOT_REFOUND
    if age is None:
        return UNCERTAIN
    if age > params.historical_years:
        return HISTORICAL
    if age <= params.recent_years:
        return STRONG if len(set(present)) >= params.strong_min_years else SPORADIC
    return UNCERTAIN
