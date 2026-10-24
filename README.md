# Species Data (SLU Artdatabanken)

A QGIS plugin for building dot maps of vascular plant observations from the Artportalen data held by SLU Artdatabanken, without needing to know APIs or filter languages.

> **Independent plugin.** This plugin is community-developed. It is not developed, owned or endorsed by SLU or SLU Artdatabanken. Data is retrieved from SLU Artdatabanken's Species Observation System under their API terms. Observation data is provided by SLU Artdatabanken; see their [API terms](https://www.slu.se/artdatabanken/rapportering-och-fynd/oppna-data-och-apier/api-villkor/).

Compatible with QGIS 3.44 up to 4.99 (Qt5 and Qt6). The user interface is in English and Swedish.

## What it does

The panel has five collapsible sections, in the same order as SLU Artdatabanken's own search page (Fynddata):

- **Taxa:** one or more names, one per line, matched ignoring case. A species name (`Anemone nemorosa`, `vitsippa`) matches exactly. A genus (`Anemone`, or its Swedish name `sippor`) includes all its species. Names that match nothing in the data are flagged. A Swedish genus name can only be resolved when the data has observations identified to that genus.
- **Time:** all years, current year, previous year, last 5 or 25 years, or a custom range.
- **Geography:** the current map extent, a county, or all of Sweden.
- **Properties:** occurrence (observed, not found, both), maximum coordinate uncertainty, uncertain identifications, verified only, red list categories.
- **Extra fields:** optional fields such as habitat and quantity. Free text remarks are off by default because they can contain personal data.

**Count observations** shows how many observations match, without downloading them. **Fetch and show observations** counts if needed, asks for confirmation above 2 000 observations, refuses above 100 000, downloads the observations in the background with a progress bar, and adds them as a temporary layer, coloured by year. Save the layer with QGIS' own tools (the memory layer indicator, or *Export > Save Features As*).

Limits of this version: vascular plants only, Artportalen data only, no protected (sensitive) observations, no API key needed.

## Data, personal data and terms

- Data comes from SLU Artdatabanken's open WFS service. Using it is subject to their terms of use. Data providers may have different licences: see the `datasetName` field. The layer metadata states the source and the date of retrieval.
- Personal data fields (`recordedBy`, `reportedBy`) are never downloaded.
- The plugin sends one request per page of results and a few small requests when counting. It counts before downloading and refuses searches of 100 000 observations or more.

## Development

Link the plugin folder into your QGIS profile so changes are picked up (use the Plugin Reloader plugin):

```powershell
# Windows (run once, adjust profile name if needed)
New-Item -ItemType Junction `
  -Path "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\species_data" `
  -Target "$PWD\species_data"
```

Compile the Swedish translation once when developing with a linked folder (the `.qm` file is not committed):

```bash
python scripts/translations.py extract   # add new strings to the .ts file
python scripts/translations.py compile   # build species_data_sv.qm
```

Run the tests (they need no network and no QGIS, except `test_plugin_load.py` which is skipped without it) and the linter:

```bash
python -m pytest
ruff check .
```

Build an installable zip:

```bash
python scripts/build_zip.py   # -> dist/species_data-<version>.zip
```

Layout:

- `query.py`: the search as a neutral model, serialised to an OGC filter for the WFS (and to the REST search filter, prepared for later use).
- `counting.py`, `net.py`: counting by probing, since `resultType=hits` does not work on the service.
- `snapshot.py`, `download.py`: the field selection and the paged background download.
- `layers.py`, `styles.py`, `provenance.py`: the temporary layer, its style, and the source metadata.
- `dockwidget.py`, `plugin.py`: the panel and the plugin class.
- `docs/`: findings about the services (`findings.md`), the Fynddata reference, the sent support mail, the API specification and a log of sources (`SOURCES.md`).

## Qt5 / Qt6 compatibility rules

- Import Qt only via `qgis.PyQt`, never `PyQt5` / `PyQt6`.
- Use fully scoped enums (`Qt.DockWidgetArea.RightDockWidgetArea`).
- Use `exec()`, not `exec_()`.
- Put anything that differs between QGIS 3 and 4 in `species_data/compat.py`.
- plugins.qgis.org runs an automatic Qt6 check on upload (see the *Qt6 Check* tab).

## License

GPL-2.0-or-later - see [LICENSE](LICENSE).
