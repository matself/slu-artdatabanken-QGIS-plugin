# Translations

Source strings are English, written with `tr("...")` in `dockwidget.py` and `plugin.py`.
The Swedish translation lives in `species_data_sv.ts`.

```bash
python scripts/translations.py extract   # add new strings to the .ts file
python scripts/translations.py compile   # build species_data_sv.qm
```

Qt's `lrelease` is not needed: the script writes the `.qm` file itself. The `.qm` file is
not committed; `scripts/build_zip.py` compiles it, and `plugin.py` loads
`i18n/species_data_<locale>.qm` automatically. Compile it once when developing with a linked
plugin folder.
