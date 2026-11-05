# Fynddata as a UI reference

Fynddata (`fynddata.artdatabanken.se`, version 1.34.0, observed 2026-10-24) is SLU Artdatabanken's own search web app. It requires login. This note records its structure as a model for the plugin's search panel. Only the layout was read; no data was exported.

The search is a workspace with five sections, plus a "Visa fynd" button and an overview that can save the search.

## 1. Taxa
- **Include (+)** and **Exclude (-)** blocks, each with:
  - a search field "taxa/organismgrupp" with autocomplete,
  - a paste box for taxon ids, with a "Klistra in" button.
- Chosen taxa show as chips and in a "Utvalda taxa" list (Swedish name | scientific name), with CSV export.
- Option "Inkludera endast arter" (only species rank, no subspecies etc.).
- Autocomplete: typing `vitsip` suggests entries such as *Anemone nemorosa* vitsippa, and also other taxa whose Swedish names contain the text (vitsippsranunkel, vitsippsruta). Each suggestion shows scientific name followed by the matching Swedish name, with the matching part in bold, and an icon for the organism group. Several taxa can be added one after another.
- **Species lists**: red-listed species by category (RE, CR, EN, VU, NT, DD, LC, NA, NE, with "include underlying taxa"), alien species (Sweden, EU regulation 1143/2014, risk list), Habitats and Birds Directive annexes, and others (protected, forest agency signal species, protected-class, priority birds).

## 2. Tid (time)
Preset dropdown: current year, previous year, last 5 years, last 25 years, all years (default), custom.

## 3. Geografi
- Search for named areas (chip example: "Öland (Provins)"), import an area, draw an area.
- Option "Exkludera fynd utanför Sverige".

## 4. Fyndegenskaper (observation properties)
- Accuracy: "include own observation location accuracy" and max accuracy in metres.
- Occurrence: only observed (default), observed plus not recovered, observed plus not found, only not recovered plus not found, only not recovered, only not found.
- Artportalen-only properties: spontaneous / non-spontaneous, uncertain identification, activities, bird breeding criteria, invasive species management.

## 5. Dataset
- Checkbox list of data sources (Artportalen, Virtuella Herbariet, iNaturalist Sverige, Miljödata MVM, NILS and others), "select all".
- Filters on projects within Artportalen and on national data hosting.
- Links to "Om dataset", which also says which datasets hold protected observations that are hidden or generalised.

## Ideas for the plugin
- Same five groups as tabs or collapsible sections, in the same order, so Fynddata users recognise them.
- Species search with autocomplete showing scientific name plus Swedish name, multi-select with chips, and an exclude list. The autocomplete needs Dyntaxa and a key; without a key, exact names via WFS are the fallback.
- Time presets as a dropdown, with a custom range.
- Occurrence choice, max accuracy and "include uncertain identification" map directly to fields in our `Query` (`present_only`, `max_uncertainty_m`, `exclude_uncertain_identification`). "Not recovered" and "not found" correspond to WFS fields `isNotRediscoveredObservation` and `isNeverFoundObservation`, not yet in `Query`.
- Dataset selection maps to `dataProviderId` / `datasetName` in WFS. Showing dataset names is also needed for source and licence attribution.
- Red list categories as checkboxes (a list of categories rather than our single `redlisted_only` flag).
- Map extent as the area option, as the user requested; named areas and drawn polygons as the other two.
