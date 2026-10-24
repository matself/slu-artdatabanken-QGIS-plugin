# Species Data (SLU Artdatabanken)

A QGIS plugin for building dot maps of species observations from the SLU Artdatabanken Species Observation System, without needing to know APIs or filter languages.

> **Independent plugin.** This plugin is community-developed. It is not developed, owned or endorsed by SLU or SLU Artdatabanken. Data is retrieved from SLU Artdatabanken's Species Observation System under their API terms. Observation data is provided by SLU Artdatabanken; see their [API terms](https://www.slu.se/artdatabanken/rapportering-och-fynd/oppna-data-och-apier/api-villkor/).

Compatible with QGIS 3.44 up to 4.99 (Qt5 and Qt6).

## Development

Link the plugin folder into your QGIS profile so changes are picked up (use the Plugin Reloader plugin):

```powershell
# Windows (run once, adjust profile name if needed)
New-Item -ItemType Junction `
  -Path "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\species_data" `
  -Target "$PWD\species_data"
```

Build an installable zip:

```bash
python scripts/build_zip.py   # -> dist/species_data-0.1.0.zip
```

## Qt5 / Qt6 compatibility rules

- Import Qt only via `qgis.PyQt`, never `PyQt5` / `PyQt6`.
- Use fully scoped enums (`Qt.DockWidgetArea.RightDockWidgetArea`).
- Use `exec()`, not `exec_()`.
- Put anything that differs between QGIS 3 and 4 in `species_data/compat.py`.
- plugins.qgis.org runs an automatic Qt6 check on upload (see the *Qt6 Check* tab).

## License

GPL-2.0-or-later - see [LICENSE](LICENSE).
