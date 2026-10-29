# CLAUDE.md

## Källhänvisning och proveniens

Under arbetet ska du föra en löpande logg i `docs/SOURCES.md`.

Logga varje gång du:
- läser eller hämtar kod, exempel eller dokumentation från ett externt repo, en webbsida eller ett installerat paket för att lösa en uppgift
- anpassar eller porterar en konkret lösning från ett känt projekt (t.ex. ett annat QGIS-plugin, Plugin Builder-mallen, ett exempel i PyQGIS Cookbook)
- använder en kodsnutt från Stack Overflow eller liknande

Format per rad: datum | vad som gjordes | källa (URL eller repo) | licens | fil i detta projekt som påverkats.

Regler:
- Kopiera aldrig kod ordagrant från en källa utan att bevara dess licensrubrik och notera det i loggen.
- Om du är osäker på licensen, skriv "licens okänd" i stället för att gissa.
- Skilj på "läste som referens" och "kopierade/anpassade kod".
- Du kan bara logga det du faktiskt läser eller hämtar i sessionen. Skriv inte påhittade källor för mönster som kommer från din träning.

## Metodbeskrivningar

`docs/metod-lokaler.md` och `docs/metod-samvariation.md` beskriver metoderna vetenskapligt och ska hållas i takt med koden. Ändrar du algoritmen, standardvärden, klassregler, storleksval eller hur resultatet visas ska du i samma commit uppdatera texten, raden "Gäller pluginversion", den maskinläsbara raden `<!-- defaults: ... -->` och ändringshistoriken längst ned. Beskriv bara det koden faktiskt gör, och skriv inte in valideringar som inte har gjorts.
