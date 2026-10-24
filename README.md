# SLU Artdatabanken

To search, visualise and optionally download species information from SLU Artdatabanken open endpoints.

Compatible with QGIS 3.34 up to 4.99 (Qt5 and Qt6).

## Development

Link the plugin folder into your QGIS profile so changes are picked up (use the Plugin Reloader plugin):

```powershell
# Windows (run once, adjust profile name if needed)
New-Item -ItemType Junction `
  -Path "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\slu_artdatabanken" `
  -Target "$PWD\slu_artdatabanken"
```

Build an installable zip:

```bash
python scripts/build_zip.py   # -> dist/slu_artdatabanken-0.1.0.zip
```

## Qt5 / Qt6 compatibility rules

- Import Qt only via `qgis.PyQt`, never `PyQt5` / `PyQt6`.
- Use fully scoped enums (`Qt.DockWidgetArea.RightDockWidgetArea`).
- Use `exec()`, not `exec_()`.
- Put anything that differs between QGIS 3 and 4 in `slu_artdatabanken/compat.py`.
- plugins.qgis.org runs an automatic Qt6 check on upload (see the *Qt6 Check* tab).

## License

GPL-2.0-or-later - see [LICENSE](LICENSE).
