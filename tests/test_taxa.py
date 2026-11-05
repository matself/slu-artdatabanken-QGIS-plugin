"""Names below a species are folded into it. No QGIS needed."""
from species_data.taxa import species_name, summary


def test_a_subspecies_is_folded_into_its_species():
    assert species_name("Pulsatilla vulgaris subsp. vulgaris") == "Pulsatilla vulgaris"
    assert species_name("Pulsatilla vulgaris subsp. gotlandica") == "Pulsatilla vulgaris"


def test_varieties_and_forms_are_folded_too():
    assert species_name("Anemone nemorosa var. purpurea") == "Anemone nemorosa"
    assert species_name("Anemone nemorosa f. rosea") == "Anemone nemorosa"
    assert species_name("Anemone nemorosa subsp. alba var. rosea") == "Anemone nemorosa"


def test_species_and_genus_names_are_unchanged():
    assert species_name("Pulsatilla vulgaris") == "Pulsatilla vulgaris"
    assert species_name("Anemone") == "Anemone"
    assert species_name("Anemone sp.") == "Anemone sp."


def test_a_hybrid_is_kept_whole():
    hybrid = "Pulsatilla pratensis \u00d7 vulgaris subsp. vulgaris"
    assert species_name(hybrid) == hybrid
    assert species_name("Pulsatilla pratensis x vulgaris") == "Pulsatilla pratensis x vulgaris"


def test_extra_spaces_are_ignored():
    assert species_name("  Pulsatilla  vulgaris  subsp.  vulgaris ") == "Pulsatilla vulgaris"


def test_summary_counts_each_name_most_frequent_first():
    names = ["Pulsatilla vulgaris subsp. vulgaris"] * 3 + ["Pulsatilla vulgaris"] * 2
    assert summary(names) == "Pulsatilla vulgaris subsp. vulgaris (3); Pulsatilla vulgaris (2)"


def test_summary_of_equal_counts_is_alphabetical_and_of_nothing_is_empty():
    assert summary(["b", "a"]) == "a (1); b (1)"
    assert summary([]) == ""
