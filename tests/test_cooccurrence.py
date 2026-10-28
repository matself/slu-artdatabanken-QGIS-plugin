"""Co-occurrence tests. No QGIS or network needed."""
from species_data import clustering
from species_data.cooccurrence import Node, Params, find_places


def node(species, x, y=0.0, radius=10.0, observations=3, not_refound=0, category=clustering.STRONG, last=2025):
    return Node(species, x, y, radius, observations, not_refound, category, 2000, last)


def test_species_close_together_form_one_place():
    nodes = [node("A", 0), node("B", 100), node("C", 120)]
    result = find_places(nodes, ("A", "B", "C"), Params(max_gap=100))
    (place,) = result.places
    assert place.species == ("A", "B", "C") and place.all_species and len(place.members) == 3


def test_distant_localities_are_separate_places():
    nodes = [node("A", 0), node("B", 100), node("A", 5000)]
    result = find_places(nodes, ("A", "B"), Params(max_gap=100))
    assert sorted(p.species for p in result.places) == [("A",), ("A", "B")]
    assert [p.all_species for p in result.places].count(True) == 1


def test_radius_extends_the_reach():
    nodes = [node("A", 0, radius=100), node("B", 250, radius=100)]
    assert len(find_places(nodes, ("A", "B"), Params(max_gap=50)).places) == 1
    assert len(find_places(nodes, ("A", "B"), Params(max_gap=0)).places) == 2  # 250 > 0 + 100 + 100


def test_only_wanted_species_count():
    nodes = [node("A", 0), node("B", 10), node("X", 20)]
    (place,) = find_places(nodes, ("A", "B"), Params()).places
    assert place.species == ("A", "B")


def test_not_refound_only_localities_do_not_count_by_default():
    nodes = [node("A", 0), node("B", 10, observations=2, not_refound=2)]
    (place,) = find_places(nodes, ("A", "B"), Params()).places
    assert place.species == ("A",) and not place.all_species
    (place,) = find_places(nodes, ("A", "B"), Params(count_not_refound=True)).places
    assert place.all_species


def test_only_current_leaves_out_old_localities():
    nodes = [node("A", 0), node("B", 10, category=clustering.HISTORICAL, last=1990)]
    result = find_places(nodes, ("A", "B"), Params(only_current=True))
    assert [p.species for p in result.places] == [("A",)] and result.left_out == 1


def test_a_string_of_localities_is_split_by_max_radius():
    nodes = [node("AB"[i % 2], i * 100) for i in range(20)]  # 2 km long, alternating species
    whole = find_places(nodes, ("A", "B"), Params(max_gap=100, max_radius=0))
    assert len(whole.places) == 1
    split = find_places(nodes, ("A", "B"), Params(max_gap=100, max_radius=300))
    assert len(split.places) > 3
    assert sorted(m for p in split.places for m in p.members) == list(range(20))


def test_years_and_counts_per_species():
    nodes = [node("A", 0, last=2020), node("A", 50, last=2025), node("B", 60, last=2010)]
    (place,) = find_places(nodes, ("A", "B"), Params(max_gap=100)).places
    assert place.localities == {"A": 2, "B": 1}
    assert (place.first_year, place.last_year) == (2000, 2025)


def test_empty_input():
    assert find_places([], ("A",)).places == []


def test_centre_and_radius_follow_the_observations_not_the_outliers():
    heavy = [node("A", i * 10, observations=50) for i in range(3)] + [node("B", 15, observations=50)]
    outlier = node("A", 330, observations=1)
    (place,) = find_places([*heavy, outlier], ("A", "B"), Params(max_gap=400, max_radius=0)).places
    assert abs(place.x - 15) < 5
    assert place.radius < 30  # the lone outlier 315 m away is outside the 90 % core
