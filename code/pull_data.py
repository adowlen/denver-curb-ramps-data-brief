"""Pull the full Denver curb ramp and Pedestrian Demand Index layers.

Sources (City and County of Denver open data, ArcGIS FeatureServer):
- ODC_TRANS_CURBRAMPS_P layer 228 (TRANS_CURBRAMPS_P), points delineated
  from 2022 aerial imagery. A ramp point is a location, not an
  ADA-compliance finding, and CREATEDATE is a delineation / capture
  date, not a construction date.
- ODC_ADMN_PEDDEMANDINDEX_A layer 442 (ADMN_PEDDEMANDINDEX_A),
  polygons by Traffic Analysis Zone. PDI_Score 1-10 from 2020 Census
  population density plus LEHD LODES employment density, combined and
  grouped into 10 quantile groupings (service description).

Full paginated pulls with geometry (outSR 4326), saved to
data/ramps_raw.geojson + .parquet and data/pdi_raw.geojson + .parquet.
Server-side counters in data/raw_aggregates.json; pull record in
data/pull_log.json. Asserts pulled == server count for both layers.
"""
import json, pathlib
import urllib.parse, urllib.request
from collections import Counter

import pandas as pd
from shapely.geometry import shape
from shapely import wkb

HOST = "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services"
RAMPS = f"{HOST}/ODC_TRANS_CURBRAMPS_P/FeatureServer/228"
PDI = f"{HOST}/ODC_ADMN_PEDDEMANDINDEX_A/FeatureServer/442"
PAGE = 2000


def q(url, params):
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": "MachineReadable pull"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def count(base, where="1=1"):
    return q(base + "/query", {"where": where, "returnCountOnly": "true", "f": "json"})["count"]


def group(base, field, where="1=1"):
    d = q(base + "/query",
          {"where": where, "groupByFieldsForStatistics": field,
           "outStatistics": json.dumps([{"statisticType": "count",
                                         "onStatisticField": "OBJECTID",
                                         "outStatisticFieldName": "cnt"}]),
           "orderByFields": "cnt DESC", "resultRecordCount": 5000, "f": "json"})
    return [[f["attributes"][field], f["attributes"]["cnt"]]
            for f in d.get("features", [])]


def pull(base):
    total = count(base)
    feats, offset = [], 0
    while True:
        d = q(base + "/query",
              {"where": "1=1", "outFields": "*", "returnGeometry": "true",
               "outSR": 4326, "orderByFields": "OBJECTID ASC",
               "resultOffset": offset, "resultRecordCount": PAGE, "f": "geojson"})
        batch = d.get("features", [])
        feats.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    assert len(feats) == total, (len(feats), total)
    return total, feats


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    rmeta = q(RAMPS, {"f": "json"})
    pmeta = q(PDI, {"f": "json"})
    # Service descriptions live on the service root, not the layer.
    rsvc = q(RAMPS.rsplit("/FeatureServer/", 1)[0] + "/FeatureServer", {"f": "json"})
    psvc = q(PDI.rsplit("/FeatureServer/", 1)[0] + "/FeatureServer", {"f": "json"})
    rtotal, rfeats = pull(RAMPS)
    ptotal, pfeats = pull(PDI)
    (root / "data" / "ramps_raw.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": rfeats}))
    (root / "data" / "pdi_raw.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": pfeats}))

    rrows = []
    for f in rfeats:
        p = dict(f["properties"])
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates") or [None, None]
        p["lon"], p["lat"] = coords[0], coords[1]
        rrows.append(p)
    pd.DataFrame(rrows).to_parquet(root / "data" / "ramps_raw.parquet", index=False)

    prows = []
    for f in pfeats:
        p = dict(f["properties"])
        geom = f.get("geometry")
        p["geometry_wkb"] = wkb.dumps(shape(geom)) if geom else None
        prows.append(p)
    pd.DataFrame(prows).to_parquet(root / "data" / "pdi_raw.parquet", index=False)

    agg = {
        "ramps": {
            "layer_id": 228,
            "service_last_edit_ms": (rmeta.get("editingInfo") or {}).get("lastEditDate"),
            "service_description": rsvc.get("serviceDescription"),
            "total_records": rtotal, "pulled_records": len(rfeats),
            "update_status_counter_server": group(RAMPS, "UPDATE_STATUS"),
            "createuser_counter_server": group(RAMPS, "CREATEUSER"),
        },
        "pdi": {
            "layer_id": 442,
            "service_last_edit_ms": (pmeta.get("editingInfo") or {}).get("lastEditDate"),
            "service_description": psvc.get("serviceDescription"),
            "total_records": ptotal, "pulled_records": len(pfeats),
            "pdi_score_counter_server": group(PDI, "PDI_Score"),
            "pdi_ranking_counter_server": group(PDI, "PDI_Ranking"),
        },
    }
    (root / "data" / "raw_aggregates.json").write_text(json.dumps(agg, indent=2))
    (root / "data" / "pull_log.json").write_text(json.dumps({
        "pull_date": "2026-10-28",
        "ramps": {"dataset": "ODC_TRANS_CURBRAMPS_P", "layer_id": 228,
                  "service_url": RAMPS, "total_records_server": rtotal,
                  "pulled_records": len(rfeats),
                  "service_last_edit_ms": agg["ramps"]["service_last_edit_ms"],
                  "update_status_counter_local": Counter(
                      str(f["properties"]["UPDATE_STATUS"]) for f in rfeats).most_common()},
        "pdi": {"dataset": "ODC_ADMN_PEDDEMANDINDEX_A", "layer_id": 442,
                "service_url": PDI, "total_records_server": ptotal,
                "pulled_records": len(pfeats),
                "service_last_edit_ms": agg["pdi"]["service_last_edit_ms"],
                "pdi_score_counter_local": Counter(
                    str(f["properties"]["PDI_Score"]) for f in pfeats).most_common(),
                "pdi_ranking_counter_local": Counter(
                    str(f["properties"]["PDI_Ranking"]) for f in pfeats).most_common()},
    }, indent=2))
    print("ramps server", rtotal, "pulled", len(rfeats),
          "last_edit_ms", agg["ramps"]["service_last_edit_ms"])
    print("pdi server", ptotal, "pulled", len(pfeats),
          "last_edit_ms", agg["pdi"]["service_last_edit_ms"])


if __name__ == "__main__":
    main()
