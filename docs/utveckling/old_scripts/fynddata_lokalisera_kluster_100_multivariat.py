import json
import math
import sys
from pathlib import Path

# ------------------------------------------------------------
# Helper: convert lat/lon to approximate meter coordinates
# ------------------------------------------------------------
R = 6371000.0
def ll_to_m(lat, lon):
    x = math.radians(lon) * R * math.cos(math.radians(lat))
    y = math.radians(lat) * R
    return x, y

# ------------------------------------------------------------
# Main program
# ------------------------------------------------------------
if len(sys.argv) < 2:
    print("Usage: python fynddata_lokalisera_kluster_100_multivariat.py <input_geojson>")
    sys.exit(1)

input_path = Path(sys.argv[1])
if not input_path.exists():
    print(f"File not found: {input_path}")
    sys.exit(1)

output_html = input_path.with_suffix(".html")

# Load input GeoJSON
geo = json.loads(input_path.read_text(encoding="utf-8"))

# ------------------------------------------------------------
# CLUSTERING INTO 100m "LOKALER"
# ------------------------------------------------------------
cells = {}
years_global = []

for f in geo.get("features", []):
    geom = f.get("geometry") or {}
    if geom.get("type") != "Point":
        continue
    coords = geom.get("coordinates") or []
    if len(coords) != 2:
        continue

    lon, lat = coords
    props = f.get("properties") or {}

    # Datum: Fynddata har Startdatum, ev. fallback Slutdatum
    t = props.get("Startdatum") or props.get("Slutdatum")
    if not t:
        continue

    try:
        year = int(str(t)[:4])
    except Exception:
        continue

    # "Ej återfunnen" / "Aldrig funnen" motsvarar gamla notRedisc
    not_redisc = bool(props.get("Ej återfunnen")) or bool(props.get("Aldrig funnen"))

    # Fynddata-exporten saknar en direkt motsvarighet till "removed"
    removed = False

    species = props.get("Vetenskapligt namn") or "Okänd"

    x, y = ll_to_m(lat, lon)

    ix = int(round(x / 100.0))
    iy = int(round(y / 100.0))
    key = (ix, iy)

    rec = {
        "lat": lat,
        "lon": lon,
        "year": year,
        "notRedisc": not_redisc,
        "removed": removed,
        "species": species,
    }

    cells.setdefault(key, []).append(rec)
    years_global.append(year)

min_year = min(years_global) if years_global else 2000
max_year = max(years_global) if years_global else 2025

# ------------------------------------------------------------
# AGGREGATE & CLASSIFY LOCAL POPULATION TRENDS
# ------------------------------------------------------------
lokaler = []

for (ix, iy), recs in cells.items():

    years_present = [r["year"] for r in recs if not r["notRedisc"] and not r["removed"]]
    years_notRedisc = [r["year"] for r in recs if r["notRedisc"]]
    years_removed = [r["year"] for r in recs if r["removed"]]

    all_years = years_present + years_notRedisc + years_removed
    if not all_years:
        continue

    first_year = min(all_years)
    last_year = max(all_years)
    last_present_year = max(years_present) if years_present else None

    n_present = len(years_present)
    n_notRedisc = len(years_notRedisc)
    n_removed = len(years_removed)

    # Classification
    category = "Osäker"

    if n_removed > 0:
        category = "Avlägsnad lokal"
    else:
        if n_notRedisc > 0 and (last_present_year is None or max(years_notRedisc) >= last_present_year):
            if max_year - max(years_notRedisc) <= 15:
                category = "Ej återfunnen"

        if category == "Osäker" and last_present_year is not None and max_year - last_present_year > 15:
            category = "Historisk lokal (inga sentida fynd)"

        if category == "Osäker" and last_present_year is not None and max_year - last_present_year <= 5 and len(set(years_present)) >= 5:
            category = "Stark aktuell lokal"

        if category == "Osäker" and last_present_year is not None and max_year - last_present_year <= 5:
            category = "Sporadisk aktuell lokal"

    # Artantal i klustret (oavsett tidsperiod/status)
    species_set = sorted(set(r["species"] for r in recs))
    n_species = len(species_set)

    # Lokalens medelpunkt
    lat_avg = sum(r["lat"] for r in recs) / len(recs)
    lon_avg = sum(r["lon"] for r in recs) / len(recs)

    lokaler.append({
        "lat": lat_avg,
        "lon": lon_avg,
        "firstYear": first_year,
        "lastYear": last_year,
        "lastPresentYear": last_present_year,
        "nPresent": n_present,
        "nNotRedisc": n_notRedisc,
        "nRemoved": n_removed,
        "category": category,
        "nSpecies": n_species,
        "species": species_set,
    })

# ------------------------------------------------------------
# CREATE SELF-CONTAINED HTML FILE WITH EMBEDDED DATA
# ------------------------------------------------------------
lokaler_js = json.dumps(lokaler, ensure_ascii=False)

html = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="utf-8" />
<title>Lokaler – 100m kluster – {input_path.stem}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<style>
  body {{ margin: 0; padding: 0; }}
  #map {{ width: 100vw; height: 100vh; }}
  .legend-box {{
    position: absolute;
    top: 10px;
    left: 10px;
    z-index: 9999;
    background: white;
    padding: 10px;
    border-radius: 8px;
    font-family: Arial, sans-serif;
    box-shadow: 0 0 6px rgba(0,0,0,0.3);
    font-size: 12px;
  }}
  .controls-box {{
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 9999;
    background: white;
    padding: 10px;
    border-radius: 8px;
    font-family: Arial, sans-serif;
    box-shadow: 0 0 6px rgba(0,0,0,0.3);
    font-size: 12px;
  }}
  .controls-box label {{ display: block; margin-bottom: 4px; cursor: pointer; }}
</style>
</head>

<body>
<div id="map"></div>

<div class="legend-box" id="legend"></div>

<div class="controls-box">
  <strong>Tematisering</strong><br>
  <label><input type="radio" name="theme" value="category" checked> Lokalstatus (category)</label>
  <label><input type="radio" name="theme" value="nSpecies"> Artrikedom (antal följearter)</label>
</div>

<script>
var lokaler = {lokaler_js};

const map = L.map('map').setView([55.9, 14.0], 8);
L.tileLayer("https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
}}).addTo(map);

function catColor(c) {{
  if (c === "Stark aktuell lokal") return "#1a9850";
  if (c === "Sporadisk aktuell lokal") return "#91cf60";
  if (c === "Historisk lokal (inga sentida fynd)") return "#cccccc";
  if (c === "Ej återfunnen") return "#fdae61";
  if (c === "Avlägsnad lokal") return "#d73027";
  return "#2b83ba";
}}

// Färgskala för artrikedom 1-4 (sekventiell, ljus -> mörk)
function speciesColor(n) {{
  if (n >= 4) return "#084594";
  if (n === 3) return "#4292c6";
  if (n === 2) return "#9ecae1";
  return "#6baed6";
}}

const legends = {{
  category: `
    <strong>Lokalstatus</strong><br>
    <span style="color:#1a9850;">●</span> Stark aktuell lokal<br>
    <span style="color:#91cf60;">●</span> Sporadisk aktuell lokal<br>
    <span style="color:#cccccc;">●</span> Historisk lokal<br>
    <span style="color:#fdae61;">●</span> Ej återfunnen<br>
    <span style="color:#d73027;">●</span> Avlägsnad lokal<br>
    <span style="color:#2b83ba;">●</span> Osäker<br>
    <br>Totalt antal lokaler: {len(lokaler)}
  `,
  nSpecies: `
    <strong>Artrikedom (antal följearter)</strong><br>
    <span style="color:#6baed6;">●</span> 1 art<br>
    <span style="color:#9ecae1;">●</span> 2 arter<br>
    <span style="color:#4292c6;">●</span> 3 arter<br>
    <span style="color:#084594;">●</span> 4 arter<br>
    <br>Totalt antal lokaler: {len(lokaler)}
  `
}};

let currentTheme = "category";
let markers = [];

function colorFor(l, theme) {{
  return theme === "nSpecies" ? speciesColor(l.nSpecies) : catColor(l.category);
}}

function popupFor(l) {{
  return `<strong>${{l.category}}</strong><br>
     Första år: ${{l.firstYear}}<br>
     Sista år: ${{l.lastYear}}<br>
     Sista år med fynd: ${{l.lastPresentYear || "–"}}<br>
     Noterad: ${{l.nPresent}}<br>
     Ej återfunnen: ${{l.nNotRedisc}}<br>
     Avlägsnad: ${{l.nRemoved}}<br>
     Antal följearter: ${{l.nSpecies}}<br>
     Arter: ${{l.species.join(", ")}}`;
}}

function draw(theme) {{
  markers.forEach(m => map.removeLayer(m));
  markers = [];
  lokaler.forEach(l => {{
    const size = 4 + Math.min(16, l.nPresent + l.nNotRedisc + l.nRemoved);
    const marker = L.circleMarker([l.lat, l.lon], {{
      radius: size,
      color: colorFor(l, theme),
      fillColor: colorFor(l, theme),
      fillOpacity: 0.7,
      weight: 1
    }}).bindPopup(popupFor(l));
    marker.addTo(map);
    markers.push(marker);
  }});
  document.getElementById("legend").innerHTML = legends[theme];
}}

document.querySelectorAll('input[name="theme"]').forEach(el => {{
  el.addEventListener("change", e => {{
    currentTheme = e.target.value;
    draw(currentTheme);
  }});
}});

draw(currentTheme);
</script>

</body></html>
"""

# Save file
output_html.write_text(html, encoding="utf-8")
print(f"Generated HTML: {output_html}")
