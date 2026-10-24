# Phase 0 findings

Checklist from PLAN.md section 3. Status: confirmed, rejected, or open.
Tested 2026-10-24 against the open WFS (no key) from Python and from QGIS 3.44.2 (Windows, profile `default`).

## 1. Long `dyntaxaTaxonId IN (...)` lists on WFS
Open. Not tested.

## 2. `resultType=hits` on WFS 1.0.0
**Rejected.** `numberOfFeatures="0"` is returned even for filters with many matches. It cannot be used for counting.

Working alternative: probe with `startIndex=N&maxFeatures=1` and check whether a feature comes back.
- To test a threshold (for example 2000), one request with `startIndex=1999` is enough.
- A full count by doubling plus bisection took 30 requests and about 6 seconds for a 16 000 feature result.
- Default ordering during paging is `endDate` descending and `sortBy` is not supported, so the count can drift slightly while data changes (15 978 by probing vs 15 967 iterated in QGIS minutes apart). Treat counts as approximate.

## 3. REST GeoJSON CRS and fields
Open. Needs an API key.

## 4. Real `take` cap
Open. Needs an API key.

## 5. One key for SOS and Taxonomy, rate limits
Open. Asked in the support mail (question 6).

## 6. Do the API terms cover WFS?
Open. Asked in the support mail (question 4).

## 7. QGIS OAuth2 with PKCE
Not applicable. The plugin will never handle protected observations (decision 2026-10-24).

## 8. QGIS WFS provider with filters and paging
Tested in QGIS 3.44.2 with `version=1.0.0`, `pagingEnabled=true`, `pageSize=1000`, `srsname=EPSG:3006`.

- The URI parameter `filter` does **not** accept CQL. It takes a QGIS expression or an OGC XML filter. The layer was invalid when given CQL.
- The QGIS expression filter cannot translate boolean literals (log: `Expression to OGC Filter error: Literal type not supported: 1`), so `isPresentObservation=true` cannot be sent that way.
- **CQL works when appended to the service URL**: `url='https://sosgeo.artdata.slu.se/geoserver/SOS/ows?CQL_FILTER=<url-encoded CQL>'`. The result was filtered correctly (municipality Lund, vascular plants) and the extra `isPresentObservation=true` term gave fewer features than the same query without it.
- **QGIS paging goes past 5000.** One layer loaded 15 967 features. The 5000 cap applies per request only. A QGIS WFS layer can therefore pull tens of thousands of features (up to startIndex 100 000), which is slow (about 23 seconds for 16 000) and heavy on the server. Counting before creating the layer is required, and the user needs a hard limit to choose, not just a warning.
- `restrictToRequestBBOX='1'` is accepted by the provider; the effect on requests was not inspected.

### Update: the filter must be OGC XML, not CQL
- `bbox` and `CQL_FILTER` are mutually exclusive on the service ("bbox and cql_filter both specified but are mutually exclusive").
- CQL `BBOX(...)` and `INTERSECTS(...)` fail in the service's CQL parser.
- An OGC XML filter (`filter=` parameter) combines everything and works: equality, case-insensitive `PropertyIsLike`, `Or`, booleans, dates, `ogc:BBOX` and `ogc:Intersects`. The geometry attribute is `point` (the other is `pointLocation`).
- Spatial coordinates in the filter work in `EPSG:4326` with longitude,latitude order (`gml:Box` and `gml:Polygon`), while `srsName=EPSG:3006` still returns SWEREF 99 TM geometries.
- `Query.to_ogc_filter()` replaces the CQL serialiser. For QGIS, the QGIS `filter` URI parameter takes an OGC filter, so the same string can be given there (not yet tested in the provider).

### Name search on WFS (no key needed)
- `scientificName` and `vernacularName` can be matched exactly and case-insensitively, several at once, with `PropertyIsLike matchCase="false"`. The Swedish names are stored in lower case (`gullviva`).
- Some records are only identified to group level (for example scientific name `Tracheophyta`, Swedish name `kärlväxter`). They have the right organism group and appear in area searches but not in name searches. The UI may want an option to hide them.
- A name picker (autocomplete, synonyms, underlying taxa) still needs Dyntaxa and therefore a key. Without one, exact names are the only option.

## 9. `url` and `recordedBy` always filled?
Open.

## Other
- The WFS name of the geometry attribute is still unknown (needed for any CQL `BBOX(...)`).
- Date fields are UTC instants of Swedish local time. Date-only observations span from the previous day 22:00Z or 23:00Z to the day itself 21:59:59Z or 22:59:59Z. Range filters in `species_data/query.py` are built around this and should be checked against Artportalen's web counts.
