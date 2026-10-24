# Källor och proveniens

Löpande logg enligt reglerna i `CLAUDE.md`. Format: datum | vad som gjordes | källa | licens | berörd fil.
"Läste som referens" betyder att ingen kod har kopierats. Posterna nedan är bara sådant som lästes eller hämtades under arbetet, inte mönster från modellens träning.

| Datum | Vad som gjordes | Källa | Licens | Berörda filer |
|---|---|---|---|---|
| 2026-10-24 | Läste som referens: API-villkoren (punkterna 2.1, 2.2, 2.3, 2.4, 5.2, 5.3, 5.6) för namn, källhänvisning och godkännande | https://www.slu.se/artdatabanken/rapportering-och-fynd/oppna-data-och-apier/api-villkor/ | Användarvillkor, ingen öppen licens | `PLAN.md`, `species_data/metadata.txt`, `README.md`, `species_data/provenance.py`, `docs/supportmail-skickat.md` |
| 2026-10-24 | Läste som referens: WFS-dokumentationen (versioner, gränser, filterexempel, kända fel) | https://github.com/biodiversitydata-se/SOS/blob/master/Docs/WfsService.md | licens okänd (repots licens kontrollerades inte) | `docs/findings.md`, `species_data/wfs.py` |
| 2026-10-24 | Läste som referens: OpenAPI-specifikationen för SOS REST (filtertyper, enum-värden) som användaren tillhandahöll | `sos-api-v1.json` i repot, från https://api.artdatabanken.se/species-observation-system/v1 | licens okänd | `species_data/query.py` (REST-serialisering), `tests/test_query.py` |
| 2026-10-24 | Läste som referens: söksidans uppbyggnad i Fynddata (sektioner, filter, hur artsökning visas). Ingen kod kopierades, bara strukturen | https://fynddata.artdatabanken.se/workspaces/default/taxa | licens okänd | `docs/fynddata-ui-reference.md`, `species_data/dockwidget.py` |
| 2026-10-24 | Läste som referens: användarens exempelexport `tests/tandrot.geojson` (fältens ifyllnadsgrad). Filen innehåller personuppgifter och checkas inte in (`.gitignore`) | lokal fil från användaren, hämtad från Artportalen via pluginet | Artportalen-data, personuppgifter | `species_data/snapshot.py` (fältval) |
| 2026-10-24 | Utgick från projektets startskelett (plugin, dockwidget, provider, `compat.py`, `build_zip.py`, CI). Ändrade namn och innehåll | https://github.com/matself/QGIS_plugin_stub ("Cookiecutter template for QGIS 3 + 4 plugins", Mats Elfströms egen mall, privat repo; angiven av användaren, repots innehåll lästes inte, bara metadata via `gh api`) | ingen licens angiven i mallrepot; upphovsman Mats Elfström. Detta projekt är GPL-2.0-or-later enligt `LICENSE` | `species_data/plugin.py`, `species_data/compat.py`, `species_data/provider.py`, `scripts/build_zip.py`, `tests/test_plugin_load.py`, `tests/test_metadata.py` |

## Egna undersökningar utan extern kodkälla

Det här är inga källor att ange, men de förklarar var fakta kommer ifrån:

- Beteendet hos den öppna WFS-tjänsten (CQL, `bbox` kontra filter, `resultType=hits`, geometrifältet `point`, `startIndex`-sökning) har testats med direkta anrop. Resultaten står i `docs/findings.md`.
- QGIS WFS-leverantörens beteende (`filter`, paginering, `restrictToRequestBBOX`) har provats i QGIS 3.44.2.
- `scripts/translations.py` skriver Qts `.qm`-format utan att Qts `lrelease` används. Formatet skrevs utifrån modellens allmänna kunskap, ingen källa lästes. Resultatet verifierades genom att ladda filen med `QTranslator` i QGIS och slå upp översättningar.
