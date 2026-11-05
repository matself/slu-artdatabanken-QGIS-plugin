# Changelog

All notable changes to Species Data (SLU Artdatabanken). The same entries, shortened, are in the `changelog` key of `species_data/metadata.txt`, which is what QGIS and plugins.qgis.org show. Keep the two in step.

## Unreleased
- A species name in the search now also finds its subspecies, varieties and forms, like the search page of SLU Artdatabanken. A Swedish species name is looked up to its scientific name for the same reason. Hybrids are not included.
- The Localities tab groups subspecies, varieties and forms under their species, and the new field `taxa` lists the names in each locality with their number of observations.

## 1.0.1 - 2026-11-05
- Security scan fix: XML escaping uses `html.escape` instead of `xml.sax.saxutils.escape`. The output is the same and the plugin parses no XML. The scanner on plugins.qgis.org flagged the old import (Bandit B406, low severity).
- CI runs Bandit at all severities.

## 1.0.0 - 2026-11-05
- First stable release.
- Waits one second between pages when fetching, to be gentle on the service.
- The plugin version is sent to the service in the `X-Requesting-System` header, read from `metadata.txt`.

## 0.2.0 - 2026-10-29
- New **Localities** tab: groups the observations of each species into localities, using the coordinate uncertainty. Size presets (strict, standard, generous), an Advanced group, an optional `locality_id` field on the observation layer, and a species list when the layer holds several species.
- New **Co-occurrence** tab: finds places where several chosen species have been reported from the same place, not necessarily at the same time, shown as points or a heat map.
- Settings are remembered between runs and stored in the metadata of each result layer, so a result can be repeated.
- Results do not depend on the order of the observations.
- The observation layer draws the coordinate uncertainty as an unfilled circle.
- Method descriptions in `docs/metod-lokaler.md` and `docs/metod-samvariation.md`.

## 0.1.0 - 2026-10-24
- Initial version: search vascular plant observations by name, period, area and properties, count before fetching, and add them as a temporary layer coloured by year. Swedish translation and user guide.
