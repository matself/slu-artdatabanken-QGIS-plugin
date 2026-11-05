"""Metadata checks that do not need QGIS."""
import configparser
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "species_data"
REQUIRED = [
    "name",
    "qgisMinimumVersion",
    "description",
    "version",
    "author",
    "email",
    "repository",
    "tracker",
]


def read_metadata():
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")
    return parser["general"]


def test_required_keys_present():
    meta = read_metadata()
    missing = [key for key in REQUIRED if not meta.get(key)]
    assert not missing, f"Missing in metadata.txt: {missing}"


def test_supports_qgis4():
    maximum = read_metadata().get("qgisMaximumVersion", "")
    assert maximum and int(maximum.split(".")[0]) >= 4, "Set qgisMaximumVersion=4.99"


def test_icon_exists():
    assert (PLUGIN_DIR / read_metadata()["icon"]).exists()


def test_license_file_exists():
    assert (PLUGIN_DIR.parent / "LICENSE").exists()


def test_the_version_sent_to_the_service_is_the_one_in_metadata():
    from species_data import provenance

    assert provenance.plugin_version() != "unknown"
    assert provenance.plugin_version().count(".") == 2


def test_the_changelog_file_has_an_entry_for_the_current_version():
    text = (PLUGIN_DIR.parent / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {read_metadata()['version']} - " in text
