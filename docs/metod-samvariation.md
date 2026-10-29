# Metod: hur samvariation mellan arter beräknas

Gäller pluginversion 0.2.0. Senast uppdaterad 2026-10-29. Koden finns i `species_data/cooccurrence.py`, och inställningarna i `species_data/settings.py` och `species_data/cooccurrence_tab.py`. Metoden bygger på lokalerna som beskrivs i [metod-lokaler.md](metod-lokaler.md).

<!-- defaults: max_gap=150 max_radius=300 only_current=false count_not_refound=false core_share=0.9 place_gap_factor=1.5 place_radius_factor=3 -->

**Det här dokumentet ska hållas i takt med koden.** Ändras algoritmen, standardvärdena eller visningen ska texten, versionsraden och ändringshistoriken längst ned uppdateras i samma commit. Ett test (`tests/test_method_docs.py`) jämför standardvärdena i raden ovan med koden.

## 1. Vad "samvariation" betyder här, och vad det inte betyder

Pluginet hittar **platser där flera valda arter har rapporterats från samma plats**. De behöver inte ha rapporterats samtidigt: fynden kan vara från olika år, och en art kan ha rapporterats för länge sedan.

Det är en rumslig sammanträffning av rapporter. Det är **inte**

- ett statistiskt samband eller en korrelation mellan arternas förekomst,
- ett test mot slumpen (det finns ingen nollmodell och inget p-värde),
- ett belägg för att arterna växer ihop i samma miljö, påverkar varandra eller har samma krav,
- ett mått på hur ofta arterna förekommer tillsammans.

Tolkningen är användarens. Resultatet beror på två urval som användaren gjort: **sökningen** av fynd (art, område, period, förekomst, källa, noggrannhet) och **lokalbildningen** (storlek och gränser). Båda står i resultatlagrets metadata. Ändras något av dem ändras platserna.

## 2. Indata

Metoden läser ett lokallager från fliken Lokaler. Per lokal används art, centrum, radie, antal fynd, antal fynd av typen "eftersökt, ej återfunnen", klass samt första och sista år. Användaren kryssar i de arter som ska ingå (minst två). Lokalerna är redan beräknade enligt [metod-lokaler.md](metod-lokaler.md), så allt som sägs där om selektion och begränsningar gäller också här.

**Vilka lokaler räknas.** En lokal ingår om dess art är vald, och

- den har minst ett fynd av närvaro, om inte alternativet *Räkna "eftersökt, ej funnen" som förekommande* är valt (standard: räknas inte), och
- den är aktuell (klassen Stark eller Sporadisk aktuell), om alternativet *Bara aktuella lokaler* är valt (standard: av).

Antalet lokaler som inte räknades redovisas.

## 3. Algoritmen

Beteckningar: G är största avstånd mellan lokaler (`max_gap`), ρ_i är lokal i:s radie och R_max största platsradie.

**Steg 1: lokalerna blir punkter.** Varje räknad lokal behandlas som en punkt vars noggrannhet är dess radie ρ_i. Stora lokaler når alltså längre.

**Steg 2: länkvillkor.** Två lokaler i och j länkas när

    avstånd(centrum_i, centrum_j) ≤ G + ρ_i + ρ_j

Länkningen är transitiv (enkellänkning), precis som för fynd. Länkarna är **inte** begränsade till olika arter. Två lokaler av samma art som ligger nära varandra kan hamna på samma plats.

**Steg 3: alla lokaler länkar fritt.** Gränserna för vaga lokaler sätts strax över den bredaste lokalen, så att brygg-regeln från lokalbildningen inte är aktiv här. Ingen lokal lämnas utanför.

**Steg 4: begränsning av platsens storlek.** Platser med radie över R_max delas med samma metod som för lokaler: de lokaler med minst radie blir mittpunkter, och övriga går till närmaste mittpunkt inom R_max eller blir egna mittpunkter. R_max = 0 stänger av delningen.

**Steg 5: beskrivning av varje plats.**

- **Arter:** de arter som har minst en lokal på platsen, och antalet arter (`n_species`).
- **Alla arter:** sant när alla valda arter finns på platsen (`all_species`).
- **Antal lokaler per art** på platsen (en kolumn per art).
- **Första och sista år** bland platsens lokaler.
- **Centrum:** lokalernas centra viktade med antal fynd.
- **Radie:** det avstånd från centrum som rymmer 90 % av fynden (viktade med antal fynd). Några enstaka lokaler i utkanten drar därför inte ut radien.
- **Numrering:** efter samma regel som för lokaler, så resultatet är oberoende av ordningen.

En plats med en enda art är med i resultatet men räknas inte som samvariation (`n_species` = 1).

## 4. Inställningar

Användaren väljer en **platsstorlek** s. Från den följer

    G = 1,5 · s        R_max = 3 · s

| Storlek | s | G | R_max |
|---|---|---|---|
| Strikt | 50 m | 75 m | 150 m |
| Standard | 100 m | 150 m | 300 m |
| Generös | 200 m | 300 m | 600 m |

Storleksvalen är pragmatiska och inte härledda ur någon art eller något habitat. Värdena kan ställas in var för sig under *Avancerat*.

## 5. Visning

- **Punkter.** Platser med alla valda arter är röda och ritas överst, platser med flera arter är blå (mörkare ju fler arter) och platser med en art är små och grå. Siffran vid punkten är antalet arter.
- **Värmekarta.** Varje plats får en vikt: platser med en art väger 0, platser med flera arter väger `n_species − 1`, och platser med alla valda arter väger ett till. Värmekartan visar alltså bara samvariation och ritas med en radie som anges i millimeter på skärmen. Vikterna är ordningsmått som valts för att göra bilden läsbar. De är inte en täthetsskattning, och bilden ändras när man zoomar eftersom radien följer skärmen och inte kartan.

## 6. Egenskaper

- **Determinism.** Samma lokaler, samma urval av arter och samma inställningar ger samma platser, oberoende av ordning.
- **Återskapande.** Inställningarna ligger i resultatlagrets metadata som JSON. Metadatan anger också arterna, sökningen och att tolkningen är användarens.

## 7. Begränsningar och risker för felläsning

1. **Rapporteringsinsats.** Platser där botanister ofta besöker och gärna rapporterar får fler arter rapporterade. Samvariation i detta mått visar delvis var man letar och rapporterar, inte bara var arterna växer. Fyndkällorna är många och deras ursprung är okänt, så insatsen går inte att räkna bort.
2. **Slumpmässig samvariation.** Vanliga arter möts på samma plats av ren slump, särskilt i områden med många rapporter. Ju större platsstorlek, desto fler sammanträffanden. Utan nollmodell går det inte att säga vad som är mer än slump.
3. **Skalberoende.** Resultatet beror på lokalstorleken (steg 1 i lokalbildningen) och platsstorleken (G och R_max). Samma fynd kan ge ett helt annat mönster med andra värden. Vi rekommenderar att köra med minst två storlekar och jämföra.
4. **Frånvaro.** Att en art inte rapporterats från en plats betyder inte att den saknas där. Samvariation som uteblir kan bero på att någon inte rapporterat.
5. **Kedjor.** Enkellänkning kan binda ihop lokaler över längre avstånd än G via mellanliggande lokaler. R_max dämpar det, men delningen följer inga naturliga gränser.
6. **Tiden.** Fynd från olika decennier kan ge en plats trots att arterna aldrig funnits där samtidigt, och en plats kan försvinna som förekomst. Alternativet *Bara aktuella lokaler* och kolumnerna för första och sista år hjälper att bedöma det, men metoden avgör det inte.
7. **Valet av arter** avgör vad som visas. En vanlig art tillsammans med en sällsynt ger främst information om den sällsynta artens lokaler.

## 8. Kontroll av metoden

- Algoritmens egenskaper testas med enhetstester i `tests/test_cooccurrence.py`.
- Utvecklaren har granskat resultatet visuellt på hämtade exempeldata (Skåne, tre och fyra arter) och jämfört platserna med fynden. Det är ingen systematisk validering och ingen jämförelse mot en annan metod.
- Idén bygger på ett äldre skript i förrådet som användes som referens. Vad som lästs och vad som inte har kopierats står i `docs/SOURCES.md`.

## Ändringshistorik

| Datum | Pluginversion | Ändring i metoden |
|---|---|---|
| 2026-10-29 | 0.2.0 | Första beskrivningen. Platser av lokaler med enkellänkning, delning vid största platsradie, platsstorlek med G = 1,5 s och R_max = 3 s, radie för 90 % av fynden, punkter och värmekarta. |
