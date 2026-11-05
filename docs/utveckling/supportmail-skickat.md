# Mejl skickat till SLU Artdatabankens support

Till: support@artportalen.se
Skickat av: Mats Elfström (datum: fyll i)
Status: skickat, inväntar skriftligt besked. Spara svaret i `docs/supportsvar.md` när det kommer.

Adress och telefonnummer i signaturen är medvetet utelämnade här, eftersom repot är öppet.

---

Hej,

Jag undersöker möjligheten för att i ett QGIS-plugin anropa Artdatabanken för att ta fram fynddata för till exempel prickkartor av artfynd från SLU Artdatabankens Species Observation System. Målgruppen är botanister och andra som arbetar med artdata i QGIS och som inte vill behöva kunna API:er eller filterspråk.

Sådana data kan i ett andra steg anpassas för fältinventeringar via mobilappen QField för QGIS.

Jag vill göra rätt från början och ber därför om ert besked i några frågor.

**Om pluginet**

* Namn: "Artdata (SLU Artdatabanken)". Namnet följer samma mönster som plugin jag publicerat för Lantmäteriets data, där källan anges i parentes efter den beskrivande delen.
* Öppen källkod (GPL-2.0-or-later), publiceras på GitHub och på plugins.qgis.org. Det är gratis att använda.
* Det är ett fristående plugin. Det framgår i pluginets metadata, README och gränssnitt att det inte ägs, utvecklas eller stöds av SLU, och att data hämtas från SLU Artdatabanken.
* Varje användare registrerar i förekommande fall eget konto och egen API-nyckel. Ingen nyckel ingår i pluginet. Nyckeln sparas i QGIS egen krypterade autentiseringshanterare, inte i projektfiler eller loggar. Se nedan fråga om var nyckel behövs.
* Pluginet visar länk till användarvillkoren och den bekräftelsemening som villkoren föreskriver (punkt 2.1) vid första start, anger SLU Artdatabanken som källa (punkt 2.3), skickar `X-Requesting-System`, räknar antal träffar innan data hämtas och cachar för att minska belastningen.
* Personuppgifter som `recordedBy` och `reportedBy` ingår inte i standardurvalet.

**Frågor**

1. Godkänner ni att pluginet distribueras som öppen källkod via GitHub och plugins.qgis.org, med användare som använder egna nycklar (punkt 5.6)?
2. Är namnet "Artdata (SLU Artdatabanken)" acceptabelt som källhänvisning enligt punkt 2.3, tillsammans med texten om att pluginet är fristående? Om ni föredrar en annan formulering anpassar jag den.
3. Får jag använda SLU Artdatabankens namn i pluginets beskrivning och i gränssnittet enbart för att ange datakällan? Finns det en logotyp eller ett föredraget sätt att ange källan?

**Förtydligande om öppna tjänster och tjänster bakom inloggning**

Jag tycker att det är svårt att förstå vad som är öppet och vad som kräver inloggning eller nyckel, och vilka villkor som gäller för vad. Det vore till stor hjälp om ni kan bekräfta följande, och gärna samla det på en sida.

4. WFS-tjänsten (`sosgeo.artdata.slu.se/geoserver/SOS/ows`) fungerar utan nyckel. Omfattas den av samma användarvillkor som REST-API:et, eller gäller andra villkor? Behöver användare av ett plugin som anropar WFS registrera sig eller ange källa på något särskilt sätt?
5. Är det avsett att WFS ska användas av klientprogram som QGIS, och finns det rekommenderade gränser för belastning? Jag har sett att `numberMatched` visar 5000 även när det verkliga antalet är större, och att endast WFS 1.0.0 fungerar. Är det kända begränsningar som ska bestå? Jag kommer antagligen att koda in en lägre gräns för att göra hanterliga dataset.
6. Gäller samma API-nyckel (prenumeration) för både observations-API:et och Taxonomy-/Dyntaxa-tjänsten, eller behövs två prenumerationer? Vilka rate limits gäller?
7. Vilket är det faktiska maxvärdet för `take` i `POST /Observations/Search`? Specifikationen anger 1000, medan informationssidan anger 10 000 per sökning.
8. Pluginet ska aldrig hantera skyddade fynd och inte kunna användas för det även om man har behörighet.

I dokumentationen finns information på flera ställen: artdatabanken.se, slu.se, GitHub-repot för SOS och utvecklarportalen. De ger delvis olika besked om vad som är öppet, vilka tjänster som kräver nyckel och vilka gränser som gäller. Det gör det svårt för en utvecklare att veta vad som är tillåtet utan att fråga. Ett förtydligande skulle hjälpa även andra som bygger verktyg på tjänsterna.

Tack på förhand. Jag publicerar inget förrän jag har ert skriftliga besked.

Vänliga hälsningar
Mats Elfström
mats.elfstrom@gmail.com
GitHub: matself
