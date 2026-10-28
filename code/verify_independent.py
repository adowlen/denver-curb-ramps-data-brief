"""Independent verifier for the Denver curb ramps brief.

Standard library only (json, collections, datetime, math, urllib).
No pandas, no shapely, no builder code. Recomputes the decisive
figures from the saved raw GeoJSON pulls with its own point-in-polygon
implementation (ray casting over a uniform grid index) and its own
area figures taken from the PDI layer's native Shape__Area field,
plus fresh live server queries. Writes
data/verify_independent_output.json and prints a summary.
Crash figures require a parquet reader and are verified here by
arithmetic closure against stats.json (the builder's crash join
carries its own controls, recorded in verification.md).
"""
import json, math, pathlib, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone

root = pathlib.Path(__file__).resolve().parent.parent
stats = json.loads((root / "stats.json").read_text())
out = {"checks_vs_builder": {}}


def chk(name, builder, mine, tol=None):
    if tol is None:
        ok = builder == mine
    else:
        ok = builder is not None and mine is not None and abs(builder - mine) <= tol
    out[name] = {"builder": builder, "independent": mine, "match": ok}
    out["checks_vs_builder"][name] = ok


# ---------- ramps: counters and dates from the raw GeoJSON ----------
ramps = json.loads((root / "data" / "ramps_raw.geojson").read_text())["features"]
props = [f["properties"] for f in ramps]
chk("total_ramps", stats["total_ramps"], len(ramps))
chk("update_status_counter", stats["update_status_counter"],
    dict(Counter(str(p["UPDATE_STATUS"]) for p in props).most_common()))
chk("createuser_counter", stats["createuser_counter"],
    dict(Counter(str(p["CREATEUSER"]) for p in props).most_common()))
chk("comments_nonnull", stats["comments_nonnull"],
    sum(1 for p in props if p["COMMENTS"] is not None))
chk("unique_id_duplicates", stats["unique_id_duplicates"],
    len(props) - len({p["UNIQUE_ID"] for p in props}))


def year_of(ms):
    if ms is None or ms <= 0:
        return "unknown"
    d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    if d.year < 1950 or d > datetime(2024, 7, 13, tzinfo=timezone.utc):
        return "unknown"
    return str(d.year)


years = Counter(year_of(p["CREATEDATE"]) for p in props)
chk("createdate_year_counter", stats["createdate_year_counter"],
    dict(sorted(years.items())))
chk("createdate_known", stats["createdate_sentinels"]["known"],
    sum(v for k, v in years.items() if k != "unknown"))

# ---------- PDI: counters, areas from native Shape__Area ----------
pdi = json.loads((root / "data" / "pdi_raw.geojson").read_text())["features"]
pprops = [f["properties"] for f in pdi]
chk("pdi_zones", stats["pdi_zones"], len(pdi))
chk("pdi_ranking_counter", stats["pdi_ranking_counter"],
    dict(Counter(str(p["PDI_Ranking"]) for p in pprops).most_common()))
score_counter = Counter(str(p["PDI_Score"]) for p in pprops)
chk("pdi_score_counter", stats["pdi_score_counter"],
    dict(score_counter.most_common()))
SQFT = 27_878_400
area_native = {}
for rk in ["LOW", "MEDIUM", "HIGH"]:
    area_native[rk] = round(sum(p["Shape__Area"] for p in pprops
                                if p["PDI_Ranking"] == rk) / SQFT, 2)
    chk(f"area_sqmi_{rk}", stats["by_ranking"][rk]["area_sqmi"],
        area_native[rk], tol=0.15)
chk("pdi_total_area_sqmi", stats["pdi_total_area_sqmi"],
    round(sum(p["Shape__Area"] for p in pprops) / SQFT, 2), tol=0.15)

# ---------- own point-in-polygon: ramps -> PDI zones ----------
def rings_of(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


zones = []  # (score, ranking, [polygons], bbox)
for f in pdi:
    polys = rings_of(f["geometry"])
    xs = [c[0] for poly in polys for ring in poly for c in ring]
    ys = [c[1] for poly in polys for ring in poly for c in ring]
    zones.append((f["properties"]["PDI_Score"], f["properties"]["PDI_Ranking"],
                  polys, (min(xs), min(ys), max(xs), max(ys))))

CELL = 0.05
grid = {}
for zi, (_, _, _, (x0, y0, x1, y1)) in enumerate(zones):
    for gx in range(int(math.floor(x0 / CELL)), int(math.floor(x1 / CELL)) + 1):
        for gy in range(int(math.floor(y0 / CELL)), int(math.floor(y1 / CELL)) + 1):
            grid.setdefault((gx, gy), []).append(zi)


def in_ring(x, y, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xin:
                inside = not inside
    return inside


def in_zone(x, y, polys):
    for poly in polys:
        if in_ring(x, y, poly[0]) and not any(in_ring(x, y, h) for h in poly[1:]):
            return True
    return False


band_ramps = Counter()
zone_ramps = [0] * len(zones)
placed = 0
for f in ramps:
    coords = (f.get("geometry") or {}).get("coordinates") or [None, None]
    x, y = coords
    hit = None
    for zi in grid.get((int(math.floor(x / CELL)), int(math.floor(y / CELL))), []):
        _, _, polys, (x0, y0, x1, y1) = zones[zi]
        if x0 <= x <= x1 and y0 <= y <= y1 and in_zone(x, y, polys):
            hit = zi
            break
    if hit is not None:
        placed += 1
        zone_ramps[hit] += 1
        band_ramps[zones[hit][1]] += 1
chk("placed_ramps", stats["placed_ramps"], placed)
for rk in ["LOW", "MEDIUM", "HIGH"]:
    chk(f"ramps_{rk}", stats["by_ranking"][rk]["ramps"], band_ramps[rk])
    dens = round(band_ramps[rk] / area_native[rk], 1)
    chk(f"ramps_per_sqmi_{rk}", stats["by_ranking"][rk]["ramps_per_sqmi"],
        dens, tol=1.0)
zero_zones = sum(1 for z in zone_ramps if z == 0)
chk("zero_ramp_zones_total", len(stats["zero_ramp_zones_all"]), zero_zones)
chk("high_zero_ramp_zones", stats["by_ranking"]["HIGH"]["zero_ramp_zones"],
    sum(1 for zi, z in enumerate(zone_ramps)
        if z == 0 and zones[zi][1] == "HIGH"))

# ---------- crash block: arithmetic closure only (parquet, no stdlib reader) ----------
cbr = stats["crashes_by_ranking"]
chk("crash_partition_crashes", stats["join_crashes_to_pdi"]["matched"],
    sum(v["crashes"] for v in cbr.values()))
chk("crash_partition_ped", stats["ped_crashes"]["in_pdi_zones"],
    sum(v["ped_crashes"] for v in cbr.values()))
for rk, v in cbr.items():
    chk(f"ped_share_recompute_{rk}", v["ped_share_of_crashes_pct"],
        round(100.0 * v["ped_crashes"] / v["crashes"], 1))
nr = stats["nearest_ramp_ped_crashes"]
chk("nearest_within150_pct_recompute", nr["within_150ft_pct"],
    round(100.0 * nr["within_150ft"] / nr["n"], 1))

# ---------- fresh live server queries ----------
def q(url, params):
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": "MR verify"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


BR = ("https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/"
      "ODC_TRANS_CURBRAMPS_P/FeatureServer/228")
BP = ("https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/"
      "ODC_ADMN_PEDDEMANDINDEX_A/FeatureServer/442")
out["live_total_ramps"] = q(BR + "/query", {"where": "1=1",
                            "returnCountOnly": "true", "f": "json"})["count"]
out["live_total_pdi"] = q(BP + "/query", {"where": "1=1",
                          "returnCountOnly": "true", "f": "json"})["count"]
chk("live_total_ramps", stats["total_ramps"], out["live_total_ramps"])
chk("live_total_pdi", stats["pdi_zones"], out["live_total_pdi"])
d = q(BR + "/query", {"where": "1=1", "groupByFieldsForStatistics": "UPDATE_STATUS",
                      "outStatistics": json.dumps([{"statisticType": "count",
                      "onStatisticField": "OBJECTID", "outStatisticFieldName": "cnt"}]),
                      "resultRecordCount": 100, "f": "json"})
live_status = {f["attributes"]["UPDATE_STATUS"]: f["attributes"]["cnt"]
               for f in d["features"]}
chk("live_update_status", stats["update_status_counter"], live_status)
d = q(BP + "/query", {"where": "1=1", "groupByFieldsForStatistics": "PDI_Ranking",
                      "outStatistics": json.dumps([{"statisticType": "count",
                      "onStatisticField": "OBJECTID", "outStatisticFieldName": "cnt"}]),
                      "resultRecordCount": 100, "f": "json"})
live_rank = {f["attributes"]["PDI_Ranking"]: f["attributes"]["cnt"]
             for f in d["features"]}
chk("live_pdi_ranking", stats["pdi_ranking_counter"], live_rank)

out["all_match"] = all(out["checks_vs_builder"].values())
(root / "data" / "verify_independent_output.json").write_text(json.dumps(out, indent=2))
print(json.dumps({"all_match": out["all_match"],
                  "failed": [k for k, v in out["checks_vs_builder"].items() if not v],
                  "placed_ramps_independent": placed,
                  "band_ramps_independent": dict(band_ramps)}, indent=2))
