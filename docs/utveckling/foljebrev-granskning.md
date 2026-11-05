# Följebrev: granskning av QGIS-pluginet Artdata (SLU Artdatabanken)

Utkast, ej skickat. Bifoga `dist/species_data-0.1.0.zip` och, om det passar, `docs/anvandarhandledning.md`.

---

**Ämne:** Testversion av QGIS-plugin för prickkartor av kärlväxter från Artportalen, för granskning

Hej,

Jag har byggt ett litet QGIS-plugin som gör prickkartor av fynd av kärlväxter i Artportalen, med SLU Artdatabankens öppna WFS-tjänst som källa. Det är fristående och inget som SLU äger eller står bakom, och det namnges och märks så i pluginet. Jag skrev tidigare till support@artportalen.se om godkännande och om namnet "Artdata (SLU Artdatabanken)"; jag publicerar ingenting innan jag fått ert besked. Det här är en testversion som ni får titta på först.

**Vad som bifogas**
- `species_data-0.1.0.zip`: pluginet, färdigt att installera
- `anvandarhandledning.md`: bruksanvisning på svenska

**Installera (några minuter)**
1. QGIS 3.44 eller senare. Inget konto eller API-nyckel behövs.
2. *Tillägg > Hantera och installera tillägg > Installera från ZIP*, välj filen och installera.
3. Klicka på vitsippsikonen i verktygsraden, eller välj *Tillägg > Artdata (SLU Artdatabanken)*. Panelen öppnas till höger.

**Så här kan ni prova**
1. Zooma in på ett område, till exempel Lund, och skriv `vitsippa` i artfältet. Tryck *Räkna fynd* och sedan *Hämta och visa fynd*. Punkterna färgas efter år, och karttips visar art, datum, plats och antal när ni håller pekaren över en punkt.
2. Skriv ett släktnamn, till exempel `Anemone` eller `sippor`, för att få alla arter i släktet.
3. Skriv ett felstavat namn, till exempel `vitsipa`, för att se varningen.
4. Kryssa i *Alla arter*, välj *CR, EN, VU, NT* under Fyndegenskaper och zooma in på ett litet område.

**Det jag särskilt skulle vilja ha synpunkter på**
- Är källangivelsen och texten om att pluginet är fristående tillräckliga och tydliga (panelen, lagrets metadata, bruksanvisningen)?
- Är namnet "Artdata (SLU Artdatabanken)" lämpligt som källhänvisning?
- Är belastningen på WFS-tjänsten rimlig? Pluginet räknar först (cirka 20 till 30 små anrop, och två anrop om träffarna är över 100 000), varnar från 2 000 fynd, vägrar över 100 000 och hämtar sedan 1 000 fynd per anrop, i bakgrunden. Alla anrop har huvudet `X-Requesting-System`.
- Går det att förstå och använda utan instruktion?
- Vilka fel eller förbättringar ser ni?

**Att veta**
- Bara kärlväxter och bara fynd från Artportalen i den här versionen. Inga skyddsklassade fynd.
- Personuppgiftsfälten (`recordedBy`, `reportedBy`) hämtas inte, och fritext i anmärkningar är avstängd som standard.
- Pluginet är märkt experimentellt. Kodförrådet är inte publikt än, så länkarna i pluginets metadata fungerar inte för er ännu. Säg till om ni vill ha källkoden tillsammans med det här.
- Lagret som skapas är tillfälligt. Spara det med QGIS egna verktyg (*Exportera > Spara objekt som*).

Svar och synpunkter tas tacksamt emot på den här adressen.

Vänliga hälsningar
Mats Elfström
mats.elfstrom@gmail.com
