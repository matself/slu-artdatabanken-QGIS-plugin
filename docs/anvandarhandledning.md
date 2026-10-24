# Bruksanvisning: Artdata (SLU Artdatabanken)

Den här handledningen är på svenska och hör till version 0.1.0 av pluginet. En engelsk beskrivning finns i [README.md](../README.md).

> **Fristående plugin.** Pluginet är utvecklat av en privatperson. Det ägs, utvecklas och stöds inte av SLU eller SLU Artdatabanken. Fynddata hämtas från SLU Artdatabankens Species Observation System (Artportalen) enligt deras API-villkor.
>
> **Testversion.** Pluginet är märkt experimentellt och är inte publicerat. Synpunkter välkomnas, se sist i det här dokumentet.

## 1. Vad pluginet gör

Pluginet gör prickkartor av fynd av kärlväxter i Artportalen, direkt i QGIS, utan att man behöver kunna API:er eller filterspråk. Man anger art eller släkte, tid, område och några fyndegenskaper, ser hur många fynd som matchar, och får ett punktlager på kartan, färgat efter år.

Begränsningar i den här versionen:

- bara kärlväxter (organismgruppen Kärlväxter)
- bara fynd från Artportalen (inte iNaturalist, herbariedata och andra dataset)
- inga skyddsklassade fynd (de finns inte i den öppna tjänsten)
- inget konto eller API-nyckel behövs, men det går inte att använda de delar av SLU Artdatabankens API som kräver nyckel

## 2. Installera

Krav: QGIS 3.44 eller senare, och internetanslutning.

1. Öppna **Tillägg > Hantera och installera tillägg...** (på engelska *Plugins > Manage and Install Plugins...*).
2. Välj fliken **Installera från ZIP**.
3. Välj filen `species_data-0.1.0.zip` och klicka **Installera tillägg**. Svara OK om QGIS varnar för att installera från en fil.
4. Se till att **Artdata (SLU Artdatabanken)** är ikryssat under fliken **Installerade**.

Pluginet visas som en vitsippsikon i verktygsraden och som **Tillägg > Artdata (SLU Artdatabanken)**. Klicka på det för att öppna eller stänga panelen, som dockas till höger. Panelen är på svenska om QGIS är inställt på svenska, annars på engelska.

## 3. Snabbstart

1. Zooma in på det område du är intresserad av. Ett litet område går snabbare.
2. Öppna panelen och skriv ett artnamn i **Arts- eller släktnamn**, till exempel `vitsippa`.
3. Tryck på **Räkna fynd** om du vill se antalet först.
4. Tryck på **Hämta och visa fynd**. Under tiden visas "Hämtar och visar fynd" med en förloppsindikator. När det är klart ligger ett punktlager överst i lagerlistan.
5. För pekaren över en punkt för att se art, datum, plats och antal.

## 4. Panelen

Panelen har fem hopfällbara sektioner, i samma ordning som i SLU Artdatabankens egen söksida Fynddata, och två knappar längst ner.

### Taxa

- **Arts- eller släktnamn:** ett namn per rad, vetenskapligt eller svenskt, till exempel `Anemone nemorosa`, `vitsippa`, `Primula veris` och `gullviva`. Skiftläget spelar ingen roll.
- Ett namn med två ord eller ett svenskt artnamn matchas **exakt**.
- Ett **släktnamn** på ett ord, till exempel `Anemone`, omfattar alla arter i släktet (även hybrider och underarter) och fynd som bara är bestämda till släkte.
- Ett **svenskt släktnamn**, till exempel `sippor`, slås upp till sitt vetenskapliga släkte (Anemone). Panelen skriver då "sippor är släktet Anemone: alla dess arter ingår." Det går bara för släkten som har fynd bestämda till släktnivå i datan.
- Om ett namn inte finns alls i datan, till exempel vid felstavning, står det under knapparna: "Ingen kärlväxt har namnet: …. Kontrollera stavningen." Sökningen ger då inga fynd för det namnet, men övriga namn fungerar.
- **Alla arter (inget namnfilter):** kryssa i om du vill söka utan namn. Då blir namnfältet grått. Det är tänkt för ett litet kartutsnitt eller några få rödlistekategorier, eftersom sökningen annars blir stor. Utan namn och utan den här rutan är knapparna avstängda.
- Jokertecken och "sp." fungerar inte som särskilda tecken i den här versionen.

### Tid

Alla år (förvalt), Innevarande år, Föregående år, Senaste 5 åren, Senaste 25 åren eller Anpassat med datumen **Från** och **Till**. "Senaste 5 åren" är innevarande kalenderår och de fyra föregående. Fynd som pågår över flera dagar räknas som träff om de överlappar perioden.

### Geografi

- **Aktuellt kartutsnitt** (förvalt): det du ser i kartfönstret när du trycker på en knapp. Pluginet räknar själv om utsnittet till rätt koordinatsystem, så kartans projektion spelar ingen roll.
- **Län:** välj ett av de 21 länen.
- **Hela Sverige**

### Fyndegenskaper

- **Förekomst:** *Endast observerad* (förvalt), *Endast ej funnen* eller *Observerad och ej funnen*.
- **Max koordinatosäkerhet:** i meter, "Ingen gräns" är förvalt.
- **Inkludera osäker artbestämning:** av som standard, så osäkra bestämningar tas inte med.
- **Endast verifierade fynd**
- **Rödlistekategorier:** RE, CR, EN, VU, NT, DD, LC, NA, NE. Ingen vald betyder alla. Knappen *CR, EN, VU, NT* kryssar de hotade kategorierna och NT.

### Extrafält

Standardfälten ingår alltid. Här kan du lägga till: *Habitat*, *Utvecklingsstadium*, *Projekt*, *Taxon-id (Dyntaxa)*, *Senast ändrad* och *Anmärkningar*. Anmärkningar är fritext som kan innehålla personuppgifter, och är därför avstängt som standard.

### Knapparna

- **Räkna fynd:** visar ungefär hur många fynd sökningen ger, utan att hämta dem. Det tar några sekunder upp till ungefär en halv minut, beroende på hur stor sökningen är. Antalet är ungefärligt.
- **Hämta och visa fynd:** räknar först om det behövs, och hämtar sedan fynden i bakgrunden. Du kan fortsätta arbeta i QGIS under tiden. Förloppet syns i panelen och i QGIS uppgiftshanterare (längst ned till höger), där det också går att avbryta.

Gränser vid hämtning:

- Från ungefär **2 000 fynd** frågar panelen om du vill fortsätta ("Ungefär N fynd kommer att hämtas. Fortsätta?"), eftersom så många punkter sällan behövs på en karta.
- Vid **100 000 fynd eller fler** hämtas inget. Avgränsa då sökningen med ett mindre område, kortare period eller fler villkor.
- Om sökningen inte ger några fynd visas "Inga fynd matchar sökningen" och inget lager skapas.

## 5. Resultatlagret

- **Namn:** artnamnen och antalet, till exempel `vitsippa (111)`. Vid *Alla arter* heter det `Kärlväxter (N)`.
- **Tillfälligt lager:** lagret finns bara i QGIS och försvinner när du stänger QGIS om du inte sparar det. QGIS markerar det med en liten ikon vid lagret. Spara det med ikonen (*Gör permanent*) eller högerklicka på lagret och välj **Exportera > Spara objekt som...** och välj till exempel GeoPackage. Pluginet skriver inga filer själv.
- **Färg:** varje år har en egen färg, och nyaste fynden ritas överst. Färgen för ett visst år är densamma i alla lager, så att du kan jämföra olika sökningar. Förklaringen i lagerpanelen visar årtalen.
- **Karttips:** för pekaren över en punkt för att se svenskt och vetenskapligt namn, datum, plats och antal. Pluginet slår på *Visa > Visa karttips* och gör lagret aktivt (karttips visas för det aktiva lagret). Du kan stänga av karttips i menyn Visa.
- **Koordinatsystem:** SWEREF 99 TM (EPSG:3006). QGIS ritar det i projektets koordinatsystem.
- **Öppna fyndet i Artportalen:** fältet `url` har länken. I attributtabellen går det att öppna den med Ctrl-klick.
- **Metadata:** under *Lageregenskaper > Metadata* står källan, hämtningsdatum, antal och sökvillkoren.

### Fält i lagret

Alltid med: `occurrenceId`, `url`, `scientificName`, `vernacularName`, `startDate`, `endDate`, `locality`, `municipality`, `county`, `province`, `coordinateUncertaintyInMeters`, `isVerified`, `redlistCategory`, `organismQuantity`, `organismQuantityUnit`, `datasetName`.

Läggs till när sökningen kan ge sådana fynd: `isPresentObservation`, `isNotRediscoveredObservation`, `isNeverFoundObservation` (när *ej funnen* ingår) och `isUncertainIdentification` (när osäkra bestämningar ingår). Extrafälten beskrivs ovan.

Datum är omräknade till svensk lokal tid. Antal och enhet ligger kvar som text, precis som i källan, och är ofta tomma.

## 6. Data, villkor och personuppgifter

- Källan är SLU Artdatabankens öppna WFS-tjänst för Artportalens fynd. Pluginet visar källan i panelen, i meddelandet efter hämtning och i lagrets metadata. Villkoren finns här: <https://www.slu.se/artdatabanken/rapportering-och-fynd/oppna-data-och-apier/api-villkor/>
- Personuppgiftsfälten `recordedBy` och `reportedBy` hämtas aldrig.
- Dataset kan ha olika licens. Se fältet `datasetName`, som alltid följer med.
- Fritext i anmärkningar kan innehålla personuppgifter, och hämtas bara om du själv kryssar i det.
- Vid sökning skickas ungefär 20 till 30 små anrop för att räkna, och sedan ett anrop per 1 000 fynd. Anropen identifierar sig med huvudet `X-Requesting-System`. Pluginet sparar ingen användardata och skickar ingenting annat än sökningen till tjänsten.

## 7. Tips

- Börja i litet utsnitt och med få villkor, och bygg ut efter hand.
- För en jämförelse mellan år: sök samma art flera gånger och jämför färgerna.
- För att se bara hotade arter i ett område: kryssa i *Alla arter*, välj knappen *CR, EN, VU, NT* och zooma in.
- Tryck på **Räkna fynd** innan du hämtar något stort.

## 8. Felsökning

| Det du ser | Det betyder |
|---|---|
| Knapparna är grå | Ange ett arts- eller släktnamn, eller kryssa i *Alla arter*. De är också grå medan en räkning eller hämtning pågår. |
| "Ingen kärlväxt har namnet: …" | Namnet finns inte i datan. Kontrollera stavningen. Det gäller bara kärlväxter. |
| "Ungefär 0 fynd" | Namnet finns men inte i det område, den period eller med de villkor du valt. |
| "Minst 100 000 fynd: för många. Avgränsa sökningen." | Sökningen är för stor och hämtas inte. Minska området eller perioden, eller lägg till fler villkor. |
| Punkterna syns inte | Kontrollera att lagret är ikryssat och att kartan är i rätt område. Lagret ligger överst men kan döljas av ett annat lager. |
| Räkningen eller hämtningen stannar | Tjänsten kan vara långsam eller ha ett driftavbrott (servern startas om dagligen). Avbryt i uppgiftshanteraren och försök igen om en stund. Felet visas i en ruta. |
| Lagret är borta efter omstart | Det är ett tillfälligt lager. Exportera det först, se avsnitt 5. |

## 9. Synpunkter och granskning

Det här är en första testversion. Särskilt intressant att få synpunkter på:

- om namnsökningen (art, släkte, svenskt släktnamn) är tydlig och räcker som start
- om gränserna (varning från 2 000 fynd, stopp vid 100 000) och antalet anrop är rimliga för tjänsten
- om källangivelsen och texten om att pluginet är fristående är tillräckliga och tydliga
- om pluginets namn "Artdata (SLU Artdatabanken)" är lämpligt (frågan har ställts till supporten)

Skicka synpunkter till Mats Elfström, mats.elfstrom@gmail.com, eller som ärende på kodförrådet: <https://github.com/matself/slu-artdatabanken-QGIS-plugin/issues> (kodförrådet är ännu inte publikt).
