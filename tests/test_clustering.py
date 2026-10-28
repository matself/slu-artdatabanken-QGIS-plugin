"""Clustering tests. No QGIS or network needed."""
from species_data.clustering import (
    HISTORICAL,
    NOT_REFOUND,
    SPORADIC,
    STRONG,
    Params,
    Point,
    cluster,
)


def groups(result):
    return sorted(sorted(loc.members) for loc in result.localities)


def test_exact_points_link_within_distance_only():
    points = [Point(0, 0, 2024, 5), Point(80, 0, 2024, 5), Point(500, 0, 2024, 5)]
    assert groups(cluster(points, Params(link_distance=100, max_radius=0))) == [[0, 1], [2]]


def test_uncertainty_widens_the_link_distance():
    points = [Point(0, 0, 2024, 200), Point(300, 0, 2024, 100)]
    assert groups(cluster(points, Params(link_distance=0, uncertainty_weight=1, max_radius=0))) == [[0, 1]]
    assert groups(cluster(points, Params(link_distance=0, uncertainty_weight=0, max_radius=0))) == [[0], [1]]


def test_chain_of_precise_points_is_one_locality():
    points = [Point(i * 90, 0, 2024, 5) for i in range(6)]
    assert groups(cluster(points, Params(link_distance=100, max_radius=0))) == [[0, 1, 2, 3, 4, 5]]


def test_vague_point_does_not_bridge_two_localities():
    points = [Point(0, 0, 2024, 5), Point(600, 0, 2024, 5), Point(300, 0, 2024, 400)]
    result = cluster(points, Params(link_distance=50, max_uncertainty=500, bridge_uncertainty=100, max_radius=0))
    # the vague point joins the nearest of the two (a tie goes to the first), not both
    assert len(result.localities) == 2
    bridged = cluster(points, Params(link_distance=50, max_uncertainty=500, bridge_uncertainty=1000, max_radius=0))
    assert len(bridged.localities) == 1


def test_points_above_max_uncertainty_are_left_out():
    points = [Point(0, 0, 2024, 5), Point(10, 0, 2024, 5000)]
    result = cluster(points, Params(max_uncertainty=500))
    assert result.left_out == [1]
    assert groups(result) == [[0]]


def test_missing_uncertainty_counts_as_the_largest_allowed():
    points = [Point(0, 0, 2024, 5), Point(550, 0, 2024, None)]
    result = cluster(points, Params(link_distance=50, max_uncertainty=500, bridge_uncertainty=100, max_radius=0))
    assert groups(result) == [[0, 1]]


def test_centre_is_pulled_towards_precise_points():
    points = [Point(0, 0, 2024, 1), Point(100, 0, 2024, 400)]
    (loc,) = cluster(points, Params(link_distance=0, bridge_uncertainty=1000, max_radius=0)).localities
    assert loc.x < 10
    assert loc.radius >= loc.x


def test_classes():
    params = Params(reference_year=2026)

    def only(*items):
        (loc,) = cluster(list(items), Params(reference_year=2026, link_distance=100)).localities
        return loc.category

    assert only(*[Point(0, 0, y, 5) for y in range(2021, 2026)]) == STRONG
    assert only(Point(0, 0, 2025, 5), Point(1, 0, 2025, 5)) == SPORADIC
    assert only(Point(0, 0, 2000, 5)) == HISTORICAL
    assert only(Point(0, 0, 2024, 5), Point(1, 0, 2025, 5, not_refound=True)) == NOT_REFOUND
    assert params.reference_year == 2026


def test_years_and_counts():
    points = [Point(0, 0, 2020, 5), Point(10, 0, 2024, 5), Point(20, 0, 2024, 5)]
    (loc,) = cluster(points).localities
    assert (loc.count, loc.years, loc.first_year, loc.last_year) == (3, [2020, 2024], 2020, 2024)


def test_empty_input():
    result = cluster([])
    assert result.localities == [] and result.left_out == []


def test_a_string_of_points_is_split_by_max_radius():
    string = [Point(i * 40, 0, 2024, 5) for i in range(30)]  # 1.2 km long
    whole = cluster(string, Params(link_distance=100, max_radius=0))
    assert len(whole.localities) == 1
    split = cluster(string, Params(link_distance=100, max_radius=100))
    assert 5 <= len(split.localities) <= 12
    assert sorted(m for loc in split.localities for m in loc.members) == list(range(30))
    assert all(loc.radius <= 100 for loc in split.localities)


def test_max_radius_leaves_small_localities_alone():
    points = [Point(0, 0, 2024, 5), Point(50, 0, 2024, 5)]
    assert groups(cluster(points, Params(link_distance=100, max_radius=100))) == [[0, 1]]


def test_the_result_does_not_depend_on_the_input_order():
    import random

    random.seed(7)
    points = [
        Point(random.uniform(0, 1500), random.uniform(0, 300), 2000 + i % 25, random.choice([5, 10, 50, 150, 300]))
        for i in range(400)
    ]

    def shape(order):
        shuffled = [points[i] for i in order]
        result = cluster(shuffled, Params(link_distance=100, max_radius=100))
        return sorted(
            (loc.id, tuple(sorted((shuffled[m].x, shuffled[m].y) for m in loc.members))) for loc in result.localities
        )

    order = list(range(len(points)))
    first = shape(order)
    for _ in range(3):
        random.shuffle(order)
        assert shape(order) == first
