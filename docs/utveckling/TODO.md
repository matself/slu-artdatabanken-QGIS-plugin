# Att göra inför nästa version

Skrivet 2026-11-09, efter att `export-import` mergats till `main`. Version 1.0.1 är den senast släppta. Det som är gjort men inte släppt står under *Unreleased* i [CHANGELOG.md](../../CHANGELOG.md). Mats väntar med nästa version tills det kommit feedback på den första, så listan kan växa.

Reglerna i [CLAUDE.md](../../CLAUDE.md) gäller för varje punkt: källogg, metodbeskrivningarna hålls i takt med koden, och posten i `CHANGELOG.md` och i `species_data/metadata.txt` skrivs i samma incheckning som versionshöjningen.

## 1. Markera alla / avmarkera alla i artlistan på fliken Lokaler

**Problem.** När ett lager har flera arter visar fliken Lokaler en kryssruta per art, och alla är förkryssade från början. Hämtar man ett område med många arter måste man klicka bort dem en och en för att välja en enda.

**Önskemål.** Två knappar, *Markera alla* och *Avmarkera alla*, vid artlistan.

**Var i koden.** `species_data/locality_tab.py`: `species_box` (rad ca 134), `_fill_species`, `_chosen` och `itemChanged` som anropar `_refresh`.

**Att tänka på**
- Knapparna ska ändra alla kryssrutor utan att anropa `_refresh` en gång per art. Blockera signalerna, ändra alla och anropa sedan `_refresh` en gång, som `_fill_species` redan gör.
- Vad ska hända när inga arter är valda? Idag returnerar `_chosen` en lista som kan bli tom. Starta-knappen bör vara avstängd, eller så ska användaren få veta varför inget händer. Kontrollera nuvarande beteende först.
- Artlistan är dold när det finns högst en art, så knapparna följer med den rutan.
- Lagernamnet följer valet (bara de valda arterna skrivs ut). Det ska fortsätta fungera.
- Texter i `tr(...)` ska in i `species_data/i18n/species_data_sv.ts` och `.qm` (se `scripts/translations.py`).
- Test: ett test som markerar alla och avmarkerar alla och kontrollerar `_chosen`. Hela flikens test körs i CI mot QGIS.
- Dokumentera i handledningen (avsnittet om Lokaler) och i `CHANGELOG.md`.

## 2. Sök inom en polygon eller en ruta som användaren ritar på kartan

**Problem.** Fliken Geografi på Hämta har bara *Aktuell kartutsträckning*, *Län* och *Hela Sverige*. Man kan inte avgränsa sökningen till ett eget område, till exempel ett reservat eller ett avrinningsområde.

**Önskemål.** Användaren ritar en polygon på kartan, eller drar upp en ruta, och sökningen görs inom det området.

**Det som redan finns.** `Query` kan redan ta `bbox_wgs84` och `polygon_wgs84` och göra om dem till WFS-filter (`_bbox` och `_intersects` i `species_data/query.py`). `_intersects` tar en enkel polygon med hål och avvisar andra geometrier. Det som saknas är verktyget på kartan och en rad på fliken Geografi (`_geography_tab` i `species_data/dockwidget.py`, rad ca 302). `_canvas_bbox` visar hur en kartutsträckning görs om till WGS 84.

**Att bygga**
- Ett kartverktyg: `QgsMapToolExtent` (eller en egen rektangel) för rutan och ett polygonverktyg med `QgsRubberBand` för polygonen. Avsluta med högerklick, avbryt med Esc och återställ verktyget som var aktivt tidigare.
- En ny rad på fliken Geografi, *Ritat område*, med knapparna *Rita ruta*, *Rita polygon* och *Rensa*, och en synlig markering av området på kartan så länge det gäller.
- Omräkning från kartans CRS till WGS 84 med `QgsCoordinateTransform`, för både ruta och polygon.
- Metadata: `provenance.py` beskriver `bbox_wgs84` men inte `polygon_wgs84`. Lagrets metadata och abstract ska säga vilket område som användes.
- Förloppet ska följa det som gäller för övriga sökningar (räkna först, tak på 100 000 fynd, en sekund mellan sidorna).

**Frågor att avgöra först**
- Hur stor polygon klarar WFS-anropet? Filtret skickas i anropet, och en polygon med tusentals hörn kan bli för stor. Provas live mot `sosgeo.artdata.slu.se` innan det byggs, och hörn kan förenklas om det behövs (`QgsGeometry.simplify` med en tolerans som anges för användaren).
- Ska det ritade området kunna kombineras med län, eller ersätta det? Förslag: ersätter, som *Aktuell kartutsträckning* gör idag, så att valen går ut på samma sätt.
- Ska användaren kunna välja en befintlig polygon i ett lager (markerat objekt)? Det är enklare än att rita och vanligt i QGIS. Kan tas med som ett tredje alternativ, men det är inte önskat än.
- Träffar polygonen punkter vars osäkerhetscirkel går utanför området? `Intersects` på fyndets punkt gör det inte. Det ska stå i handledningen, eftersom användare annars kan tro att allt inom cirkeln finns med.
- Hur ser kartverktyget ut för en användare som redan har ett annat verktyg aktivt, och vad händer om pluginet stängs medan verktyget är på?

**Test.** `Query` med polygon ger rätt XML (finns delvis). Nytt: kartverktygets resultat blir en giltig `polygon_wgs84`. Ett live-test mot WFS med en liten polygon, som en manuell kontroll och inte i CI.

**Dokumentation.** Handledningen (avsnittet om Hämta, fliken Geografi), `CHANGELOG.md`, och en rad i README. Metodbeskrivningarna berörs bara om valet av område förändrar vad som kallas en lokal, vilket det inte gör.

## Redan känt och öppet (från tidigare, inte ändrat här)

- En kolumn för källa (`sources`) på samvariationslagret, som lokallagret har. Erbjudet, inte beställt.
- Frågor till SLU om licens per dataset, dubbletter mellan datakällor och en lista över leverantörer.
- Mer än kärlväxter och fler källor: se [kallor-och-organismgrupper.md](kallor-och-organismgrupper.md). iNaturalist har låg prioritet.
- Engelska kolumnnamn i exporten från Fynddata: kräver en export på engelska att jämföra med.
- Skärmbild till README (läggs i `docs/images/`), som Mats tar själv.
