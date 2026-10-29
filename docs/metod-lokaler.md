# Metod: hur fynd grupperas till lokaler

Gäller pluginversion 0.2.0. Senast uppdaterad 2026-10-29. Koden finns i `species_data/clustering.py`, och inställningarna i `species_data/settings.py` och `species_data/locality_tab.py`.

<!-- defaults: link_distance=100 uncertainty_weight=1 max_uncertainty=500 bridge_uncertainty=100 max_radius=100 recent_years=5 historical_years=15 strong_min_years=5 presets=50,100,200 -->

**Det här dokumentet ska hållas i takt med koden.** Ändras algoritmen, standardvärdena eller klassreglerna ska texten, versionsraden och ändringshistoriken längst ned uppdateras i samma commit. Ett test (`tests/test_method_docs.py`) jämför standardvärdena i raden ovan med koden och slår larm om de glider isär.

## 1. Vad en lokal är, och vad den inte är

En **lokal** i pluginet är en beräkningsmässig gruppering av rapporterade fynd av en art som ligger så nära varandra att de kan vara rapporter från samma plats. Den är ett sätt att sammanfatta rapporter, inte en uppmätt biologisk enhet.

En lokal är alltså **inte** en population, en individ, en förekomstyta eller en inventerad enhet. Antalet fynd i en lokal säger hur många gånger arten har rapporterats därifrån, inte hur stor eller hur beständig förekomsten är. Fyndrapporter kommer från många olika källor och med mycket olika rapporteringsinsats. Metoden gör inga antaganden om var rapporterna kommer ifrån.

Skälet till att gruppera är praktiskt: en art som rapporteras ofta rapporteras ofta flera gånger från samma plats, av olika personer och med olika koordinatnoggrannhet, så att en plats ser ut som flera punkter.

## 2. Indata

Metoden läser ett fyndlager som hämtats med pluginet (eller sparats därifrån med metadata). Fälten som används är:

| Fält | Används till |
|---|---|
| geometri | läget, omräknat till SWEREF 99 TM (EPSG:3006) så att avstånd blir meter |
| `scientificName` | arten. Varje art grupperas för sig och lokaler bildas aldrig över artgränser |
| `endDate` | årtalet (året för fyndets slutdatum) |
| `coordinateUncertaintyInMeters` | koordinatnoggrannhet U, i meter |
| `isPresentObservation` | fynd som anger att arten saknas används inte |
| `isNotRediscoveredObservation` | fynd som anger "eftersökt, ej återfunnen" räknas med men markeras |

Konsekvenser som är värda att känna till:

- Arten är det vetenskapliga namn som tjänsten levererar. Synonymer, underarter och namnbyten behandlas som olika arter om namnen skiljer sig.
- Ett fynd utan angiven noggrannhet behandlas som om det hade den största tillåtna noggrannheten (standard 500 m).
- Fynd med angiven noggrannhet över gränsen U_max (standard 500 m) lämnas helt utanför. Antalet redovisas efter körningen. Det ger en selektion mot precisa fynd, se avsnitt 8.
- Fynd utan datum bidrar till antal fynd men inte till årtal.
- Det som hämtats ur tjänsten styrs av sökningen (art, område, period, förekomst, källa, noggrannhetsgräns). Sökningen står i lagrets metadata och är den första av de två selektioner resultatet bygger på.

## 3. Algoritmen

Beteckningar: L är länkavståndet, U_i fyndets noggrannhet, U_max gränsen för att räknas med, B gränsen för "vaga" fynd, R_max största lokalradie, w är 1 om koordinatnoggrannheten får vidga räckvidden och annars 0.

**Steg 1: urval.** Fynd med U_i större än U_max tas bort. För övriga sätts den effektiva noggrannheten u_i = w · min(U_i, U_max), där ett saknat U_i räknas som U_max.

**Steg 2: länkvillkor.** Två fynd i och j kan länkas när

    avstånd(i, j) ≤ L + u_i + u_j

Noggrannheten vidgar alltså varje fynds räckvidd med sin egen radie. Två fynd vars osäkerhetscirklar överlappar länkas, även om mittpunkterna ligger längre ifrån varandra än L.

**Steg 3: precisa fynd länkas fritt.** Fynd med U_i ≤ B kallas precisa. Alla par av precisa fynd som uppfyller länkvillkoret slås ihop, och sammanslagningen är transitiv: om A länkar till B och B till C hamnar alla tre i samma lokal även om A och C ligger längre isär än L. Det är så kallad enkellänkning (single linkage).

**Steg 4: vaga fynd fäster bara vid en lokal.** Fynd med U_i > B behandlas i ordning efter stigande noggrannhet (lika noggrannhet avgörs av koordinaterna). Varje vagt fynd går till det **närmaste** redan placerade fyndet som det uppfyller länkvillkoret mot, och slår aldrig ihop två lokaler. Ett vagt fynd utan ett sådant fynd blir en egen lokal. Regeln finns för att ett enda vagt fynd inte ska kunna binda ihop två platser som ligger skilda åt.

**Steg 5: begränsning av storleken.** Enkellänkning ger långa kedjor längs till exempel en strand eller en väg. Om en grupps radie (största avståndet från gruppens oviktade medelpunkt till ett fynd) är större än R_max delas gruppen: fynden tas i ordning efter stigande noggrannhet, varje fynd går till närmaste redan vald mittpunkt om den ligger inom R_max, och blir annars själv en ny mittpunkt. De mest precisa fynden blir alltså mittpunkter. Med R_max = 0 sker ingen delning.

**Steg 6: beskrivning av varje lokal.**

- **Centrum:** medelpunkten av fynden viktad med 1 / (1 + U_i), så att exakta fynd drar mer än vaga (saknat U_i räknas som U_max).
- **Radie:** största avståndet från centrum till ett fynds läge. Fyndens egen noggrannhet läggs inte till.
- **Antal fynd, årtal, första och sista år.**
- **Klass:** se avsnitt 4.
- **Numrering:** lokalerna numreras efter minsta x- och sedan y-koordinat bland sina fynd.

Sökningen i koordinatrummet använder ett rutnät, så att beräkningen går snabbt också för tiotusentals fynd. Rutnätet påverkar inte resultatet.

## 4. Klassning av lokaler

Referensåret Y är innevarande år vid körningen. Klassgränserna är: aktuell om senaste fyndet är högst r år gammalt (standard 5), historisk om det är äldre än h år (standard 15), och stark om lokalen har fynd från minst s olika år (standard 5). Klassen avgörs i denna ordning:

1. Om lokalen har fynd av typen "eftersökt, ej återfunnen", och antingen saknar fynd av närvaro eller har ett sådant fynd som är lika nytt som eller nyare än senaste närvarofyndet, och det är högst h år sedan, blir klassen **Ej återfunnen**.
2. Saknas fynd av närvaro med årtal blir klassen **Osäker**.
3. Är senaste närvarofyndet äldre än h år blir klassen **Historisk**.
4. Är det högst r år gammalt blir klassen **Stark aktuell** om fynden är från minst s olika år, annars **Sporadisk aktuell**.
5. I övriga fall, alltså ett senaste fynd som är äldre än r men högst h år, blir klassen **Osäker**.

Observera att:

- "Osäker" här betyder att klassen inte går att avgöra av årtalen. Det har inget med osäkra artbestämningar att göra.
- Antalet olika år (s) räknas över **alla** fynd i lokalen, inte bara de senaste r åren. En lokal med fynd från fem olika år mellan 2002 och 2024 och senaste fyndet 2024 blir alltså Stark aktuell.
- Klassningen bygger bara på årtal. Den tar inte hänsyn till rapporteringsinsats. Ett år utan fynd betyder inte att arten saknades.
- Referensåret sparas med inställningarna men används inte när inställningarna återställs: ny körning räknar mot innevarande år.

## 5. Inställningar

Användaren väljer normalt en **lokalstorlek** s, som sätter tre värden till samma tal:

| Storlek | s | L | B | R_max |
|---|---|---|---|---|
| Strikt | 50 m | 50 m | 50 m | 50 m |
| Standard | 100 m | 100 m | 100 m | 100 m |
| Generös | 200 m | 200 m | 200 m | 200 m |

Övriga värden (U_max 500 m, om noggrannheten får vidga räckvidden, och årsgränserna) ligger under *Avancerat*. Storleksvalen är pragmatiska och är inte härledda ur någon art eller något habitat. För arter med olika spridningsbiologi eller klonal tillväxt kan andra storlekar vara rimligare, och användaren förväntas välja efter sin kunskap om arten.

## 6. Egenskaper

- **Determinism.** Samma indata och samma inställningar ger samma lokaler, med samma numrering, oavsett i vilken ordning fynden ligger i lagret. Det har kontrollerats med ett test som blandar 400 punkter.
- **Artvis.** Lokaler för olika arter beräknas oberoende av varandra.
- **Löpnumret** `locality_id` går bara att jämföra inom en körning.
- **Återskapande.** Inställningarna ligger i resultatlagrets metadata som JSON, och sökningen och hämtdatumet står i metadatans text.

## 7. Avvägningen mellan kedjor och delade lokaler

Begränsningen R_max är ett val mellan två fel. Utan gräns bildar täta rader av fynd en enda mycket lång lokal. Med gräns delas sådana rader på ett sätt som är beroende av vilka fynd som råkar vara mest precisa, och delningen följer inga naturliga gränser. Ett kontinuerligt bestånd längs en strand delas i bitar, och en delningslinje kan gå mitt genom en grupp fynd som egentligen hör ihop.

I en orienterande körning på hämtade data delades ungefär 40 % av paren av överlappande osäkerhetscirklar upp i olika lokaler vid en gräns på 100 m, mot ungefär 1 % utan gräns. Siffrorna kommer från en enskild körning under utvecklingen och är en indikation, inte ett resultat. De bör återskapas innan de citeras. Gränsen kan stängas av (R_max = 0) under *Avancerat*, och valet är användarens.

## 8. Antaganden och begränsningar

1. **Rapporter, inte förekomster.** Rapporteringsinsatsen varierar mellan platser, tider och källor. Platser som besöks ofta, till exempel där det finns sällsynta arter, får fler fynd och fler år. Antal fynd och antal år mäter därför delvis rapporteringen.
2. **Noggrannhet tolkas som radie.** Koordinatnoggrannheten behandlas som ett största avstånd, inte som en sannolikhetsfördelning. Kvaliteten på angiven noggrannhet varierar mellan rapportörer och kan inte kontrolleras här.
3. **Selektion mot precisa fynd.** Fynd över U_max utesluts. Äldre fynd är ofta vagare, så historiska lokaler kan vara underrepresenterade. Valet av U_max påverkar vilka lokaler som finns.
4. **Skalberoende.** Resultatet beror på L, B och R_max. Det finns ingen "rätt" lokalstorlek. Samma fynd ger fler och mindre lokaler vid Strikt och färre och större vid Generös.
5. **Kedjor.** Enkellänkning kan koppla ihop avlägsna fynd via mellanliggande. Brygg-regeln för vaga fynd och R_max dämpar det men tar inte bort det.
6. **Taxonomi och datum.** Se avsnitt 2.
7. **Skyddade fynd** ingår inte i den öppna tjänsten, så platser med skyddade arter kan saknas helt.

## 9. Kontroll av metoden

- Algoritmens egenskaper (länkning, brygg-regeln, delning, determinism, klassning) testas med enhetstester i `tests/test_clustering.py`.
- Utvecklaren har granskat resultatet visuellt på hämtade exempeldata för några arter och bedömt att lokalerna stämmer med de kända växtplatserna. Det är ingen systematisk validering mot fältkunskap eller mot någon annan metod.
- Metoden har inget samband med någon bedömning av artens status. Den är ett hjälpmedel för att läsa fyndrapporter, inte en rödlistebedömning.

Idén att gruppera fynd efter avstånd och koordinatnoggrannhet har tidigare använts i andra verktyg. Vad som lästs som referens och vad som inte har kopierats står i `docs/SOURCES.md`.

## Ändringshistorik

| Datum | Pluginversion | Ändring i metoden |
|---|---|---|
| 2026-10-29 | 0.2.0 | Första beskrivningen. Enkellänkning med noggrannhet, brygg-regel för vaga fynd, delning av kedjor, storleksval, deterministisk ordning. |
