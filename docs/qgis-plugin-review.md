# Pre-publication review (plugins.qgis.org)

Review run 2026-10-24 with the checks of the `qgis-plugin-review` skill against `dist/species_data-0.1.0.zip`.

## Result

| Check | Result |
|---|---|
| Package (one top folder, `__init__.py`, `metadata.txt`, `LICENSE` in the plugin root, size 0.03 MB, no `.pyc`) | passed |
| Mandatory metadata keys | passed |
| Bandit (medium and high) | no findings |
| detect-secrets | no findings |
| Flake8 (max line length 120) | clean after two small fixes |
| Code, comments and docstrings in English | passed |
| Qt6 rules (`qgis.PyQt`, scoped enums, `exec()`) | `qgisMaximumVersion=4.99` set; no direct PyQt5 imports. The server's Qt6 check still has to be read after upload |
| Network access through QGIS (`QgsBlockingNetworkRequest`, so proxy settings apply) | passed |
| Links in metadata (`tracker`, `repository`, `homepage`) | **blocking until the repository is public**: the GitHub repository is private and answers 404 |

## Still to do before upload

- Make the repository public (or create the final public repository and update the three URLs in `metadata.txt`).
- Wait for the written answer from SLU Artdatabanken to the support mail (`docs/supportmail-skickat.md`): approval of distribution as open source, and of the plugin name. The mail promises that nothing is published before then.
- Create an OSGeo ID and log in on plugins.qgis.org.
- Tag the release to match the version (`v0.1.0`) and upload `dist/species_data-0.1.0.zip` (built by `scripts/build_zip.py`, which also compiles the Swedish translation).
- Check that no existing plugin already does this (search plugins.qgis.org for "Artportalen", "SBDI", "species observations").
- Optional: a PNG icon in addition to `icon.svg`, screenshots in the README, and a small test search in the README.

## Facts for the upload form

```ini
name=Species Data (SLU Artdatabanken)
qgisMinimumVersion=3.44
qgisMaximumVersion=4.99
description=Fetch vascular plant observations from Artportalen (SLU Artdatabanken) as a temporary, year-coloured point layer.
version=0.1.0
author=Mats Elfström
category=Plugins
experimental=True
license=GPL-2.0-or-later
hasProcessingProvider=no
tags=species,observations,botany,plants,artportalen,biodiversity,sweden,wfs,dot map
```

The `about` text, the changelog and the links are in `species_data/metadata.txt`. Things to state in the upload and in answers to reviewers:

- No account or API key is needed; the plugin uses the open WFS service of SLU Artdatabanken.
- Coverage: Sweden, vascular plants, Artportalen data only. No protected (sensitive) observations.
- External dependencies: none beyond QGIS.
- Personal data fields (`recordedBy`, `reportedBy`) are not requested; free text remarks are off by default.
- The user interface is in English with a Swedish translation (`i18n/species_data_sv.ts`); the README describes each section of the panel in English.
- The plugin is independent and not endorsed by SLU; the source is stated in the panel, the layer metadata and the README.
- The layer is a temporary memory layer; nothing is written to disk by the plugin.
