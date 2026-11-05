# Underlag: fler källor och fler organismgrupper

Skrivet 2026-11-05 som förberedelse för en senare version. Inget av detta är byggt. Det som står under "Provat" har kontrollerats med direkta anrop mot den öppna WFS-tjänsten (några få anrop med ett fynd var). Det som står under "Ej kontrollerat" är antaganden.

## Fråga 1: vilka andra källor kan flätas in?

### Provat
- **iNaturalist finns redan i SLU:s tjänst.** Fynd från iNaturalist har `dataProviderId` 19, `datasetName` "iNaturalist" och `institutionCode` "iNaturalist.org", och `occurrenceId` är en länk till observationen på inaturalist.org. De kommer genom samma WFS-adress och samma filter som Artportalen. Pluginet kan alltså välja dem med ett filtervillkor (`Query.dataset_ids` finns redan), utan ny datakälla, nytt API eller ny nyckel.
- **Koordinatnoggrannheten skiljer.** De tre iNaturalist-fynd som provades hade 68 m, 25 527 m och 25 527 m. Värden runt 25 km ser ut som iNaturalists dolda eller generaliserade positioner. Pluginets standardgräns på 500 m för noggrannhet (`max_uncertainty`) rensar bort sådana fynd av sig själv, men det betyder också att en del av iNaturalists fynd inte syns.
- Artportalen har `dataProviderId` 1. Någon fullständig lista över leverantörer går inte att få utan nyckel (REST `/DataProviders`). Därför vet vi inte vilka fler som finns i tjänsten, bara de två som provats.

### Ej kontrollerat
- Om iNaturalist-fynd i tjänsten är dubbletter av Artportalens fynd (samma fynd i båda). Det måste frågas SLU om.
- Vilken licens varje fynd har. Fältet `datasetName` anger källan, men något licensfält syntes inte i svaret för de fynd som provades. Pluginets metadata säger redan att leverantörer kan ha olika licenser.
- Om iNaturalists egen API-tjänst vore ett alternativ. En sökning gav att iNaturalist ber om högst ungefär 60 anrop per minut och avråder från att skrapa data via API:et till förmån för deras exportfiler, och att licensen varierar per observation (CC0, CC BY, CC BY-NC). Den exakta dagsgränsen och de aktuella villkoren bekräftades inte hos iNaturalist. Det spåret behöver ett eget kodspår, egen taxonomi och egen licenshantering, och är inte att rekommendera så länge SLU:s tjänst redan har fynden.

### Förslag
- Kryssrutor för källa under **Egenskaper**: *Artportalen* (förkryssad) och *iNaturalist* (av). Ingen annan källa tills vi vet vilka som finns.
- Tydlig märkning när fler än en källa är vald: lagrets metadata anger vilka källor som ingår och hur många fynd varje källa gav, och fältet `datasetName` finns redan i lagret.
- Lokal- och samvariationsresultaten ärver källuppgiften i metadatan, så att tolkningen går att göra. Överväg ett fält per lokal med antal fynd per källa, så att användaren kan se var blandningen drar.

### Tveksamheten om att blanda källor är välgrundad
- Artportalens fynd kommer från många olika rapportörer och inventeringar, och iNaturalists från fotografier, ofta med andra besöksmönster och osäkrare artbestämning. Metoderna i `docs/metod-lokaler.md` och `docs/metod-samvariation.md` behandlar alla fynd lika. Blandade källor gör tolkningen svårare, inte omöjlig.
- Skriv i metodbeskrivningarna att resultatet beror på vilka källor som valts, precis som på de andra urvalen, och att tolkningen är användarens.

## Fråga 2: kan svampar, lavar och mossor hämtas?

### Provat
Ja. Samma sökning med en annan organismgrupp fungerar, och `Query.organism_group` är redan en inställning. Gruppnamnen i tjänsten, som de stavas där:

| Grupp | Resultat |
|---|---|
| Kärlväxter | fungerar (det som används nu) |
| Mossor | fungerar |
| Lavar | fungerar |
| Storsvampar | fungerar (namnet är *Storsvampar*, inte *Svampar*; *Svampar* gav 0 träffar) |
| Alger | fungerar |
| Mikrosvampar, Slemsvampar | 0 träffar i Skåne med den stavningen, så namnet är fel eller gruppen tom |

Fynden har samma fält som kärlväxter (`organismGroup`, `scientificName`, `endDate`, `coordinateUncertaintyInMeters`), så klustringen, lokalerna och samvariationen fungerar utan ändring i algoritmerna. Namnsökningen på vetenskapligt namn kräver ingen grupp, så den fungerar redan för alla.

### Ej kontrollerat
- Den fullständiga listan med gruppnamn. Den går att få med REST-API:et (nyckel), genom att fråga SLU, eller genom att prova fler namn.
- Hur många fynd det blir. Svampar och lavar har många fler fynd än kärlväxter i vissa områden. Pluginets gräns på 100 000 fynd och varningen från 2 000 träffar gäller fortfarande, men fler hämtningar kommer att bli för stora.
- Om lokalbegreppet passar. En lokal definieras av avstånd och koordinatnoggrannhet. För lavar på ett träd eller mossor på en sten kan 100 m vara för grovt, och för storsvampar, som fruktkroppar ett visst år, är "lokal" ett annat begrepp. Det är en fråga för botanister och mykologer, och metodbeskrivningen behöver ett avsnitt om det.

### Förslag
- Kryssrutor under **Taxa**: *Kärlväxter* (förkryssad), *Mossor*, *Lavar*, *Storsvampar* och eventuellt *Alger*. Flera valda grupper blir ett OR-villkor.
- `Query.organism_group` blir en lista av grupper. Filtret, metadatan och raden "Organism group" ändras därefter, och texten "vascular plants only" i panelen, README, `about` och handledningen måste bytas.

## Arbetsomfattning (uppskattad)
- Kryssrutor för organismgrupp och källa, ändrat filter, metadata, översättningar, tester och dokumentation: liten till måttlig insats, eftersom filtren redan finns i `query.py`.
- Källsammansättning i resultaten och nya stycken i metodbeskrivningarna: liten insats.
- Det som kan ta längst är att få fram gruppnamnen och få klarhet i licenser och dubbletter hos SLU.

## Frågor till SLU
1. Är iNaturalist-fynd i SOS dubbletter av Artportalens fynd, eller separata?
2. Vilken licens gäller för iNaturalist-fynden som levereras genom WFS, och finns det ett fält som anger den?
3. Vilka gruppnamn (`organismGroup`) och vilka leverantörer (`dataProviderId`) finns, och går det att få listan utan nyckel?
4. Ändras något i villkoren när fynd från andra leverantörer än Artportalen hämtas?

## Källor
- Direkta anrop mot `https://sosgeo.artdata.slu.se/geoserver/SOS/ows` med pluginets egna filter, 2026-11-05.
- Sökresultat om iNaturalists API och licenser: [forum.inaturalist.org, rate limit](https://forum.inaturalist.org/t/discrepancy-between-documented-rate-limit-observed-rate-limit/8612) och [forum.inaturalist.org, lagra data](https://forum.inaturalist.org/t/are-you-allowed-to-store-inaturalist-data-from-the-api-on-your-own-server/75969). Sidorna lästes inte i sin helhet.
