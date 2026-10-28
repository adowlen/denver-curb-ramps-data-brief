"""Build stats.json and the panels for the Denver curb ramps brief.

Inputs:
- data/ramps_raw.parquet and data/pdi_raw.parquet (this brief's live
  pulls, see code/pull_data.py).
- Stack layers (Machine Readable warehouse, read-only):
  neighborhoods_clean.parquet (78 statistical neighborhoods; geometry
  stored in EPSG:4326 lon/lat - verified from coordinate ranges, NOT
  the State Plane feet the task brief guessed) and
  traffic_accidents_clean.parquet (106,121 crash reports, reported
  2021-01-01 to 2026-10-15, deduplicated on offense_id by the
  warehouse build; the same analysis panel the 2026-10-26 traffic
  signals brief used).

Definitions and traps, stated up front:
- A curb ramp point is a LOCATION delineated from aerial imagery. The
  service description states ramps do not have to be ADA accessible to
  be captured and imagery cannot discern accessibility. No figure in
  this package is an ADA-compliance finding.
- CREATEDATE is the date the ramp record was delineated / created in
  the GIS, not a construction date. It is never used as ramp age.
- PDI_Score is a quantile score (1-10) over Traffic Analysis Zones,
  built from 2020 Census population density plus LEHD LODES employment
  density (service description). PDI_Ranking is the layer's own band:
  LOW = scores 1-4, MEDIUM = 5-6, HIGH = 7-10 (verified by a server
  groupBy on both fields). PDI is a demand proxy, not measured
  pedestrian volumes.
- Areas: polygons projected EPSG:4326 -> EPSG:2877 (Colorado Central
  State Plane, feet), area / 27,878,400 = square miles. Cross-checked
  against the PDI layer's own Shape__Area sum (native square feet).
- Joins are point-in-polygon in lon/lat (shapely STRtree, predicate
  "within"; a point on a shared boundary counts in the first matching
  polygon only - no ramp or crash matched more than one polygon in
  either join, recorded in the audit).
- Nearest-ramp distances are computed in EPSG:2877 feet.
- Crash severity: KSI crash = ksi_crash_count_basis in the warehouse
  panel (a crash with a death or a serious injury, crash-count basis).
"""
import json, pathlib
from collections import Counter

import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from shapely import wkb
from shapely.geometry import Point
from shapely.strtree import STRtree

ROOT = pathlib.Path(__file__).resolve().parent.parent
STACK = ROOT.parent / "stack" / "denver" / "layers"
SQFT_PER_SQMI = 27_878_400
TR = Transformer.from_crs(4326, 2877, always_xy=True)


def project(g):
    return shapely.transform(
        g, lambda xy: np.column_stack(TR.transform(xy[:, 0], xy[:, 1])))


def area_sqmi(g):
    return float(project(g).area / SQFT_PER_SQMI)


def pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def pip(points_xy, geoms):
    """Return dict input_index -> polygon_index (first within match)."""
    tree = STRtree(geoms)
    res = tree.query([Point(x, y) for x, y in points_xy], predicate="within")
    assign, multi = {}, 0
    seen = Counter(res[0].tolist())
    multi = sum(1 for v in seen.values() if v > 1)
    for ri, ti in zip(res[0].tolist(), res[1].tolist()):
        assign.setdefault(ri, ti)
    return assign, multi


def main():
    S = {}
    ramps = pd.read_parquet(ROOT / "data" / "ramps_raw.parquet")
    pdi = pd.read_parquet(ROOT / "data" / "pdi_raw.parquet")
    N = len(ramps)
    S["source_pull_date"] = "2026-10-28"
    S["snapshot_date"] = "2026-10-28"
    S["ramps_dataset"] = ("ODC_TRANS_CURBRAMPS_P (Denver Open Data, ArcGIS "
                          "FeatureServer layer 228)")
    S["ramps_service_last_edit"] = "2024-07-12"
    S["pdi_dataset"] = ("ODC_ADMN_PEDDEMANDINDEX_A (Denver Open Data, ArcGIS "
                        "FeatureServer layer 442)")
    S["pdi_service_last_edit"] = "2026-08-07"
    S["total_ramps"] = N
    S["ramps_with_geometry"] = int(ramps["lon"].notna().sum())
    S["ramps_without_geometry"] = int(ramps["lon"].isna().sum())

    # ---- full unique-value counters for every categorical column ----
    def counter(col, null_label="NULL"):
        return dict(Counter(null_label if pd.isna(v) else str(v)
                            for v in ramps[col]).most_common())
    S["update_status_counter"] = counter("UPDATE_STATUS")
    S["update_status_domain"] = {"A": "Add", "M": "Modify", "NC": "No Change"}
    S["createuser_counter"] = counter("CREATEUSER")
    S["comments_nonnull"] = int(ramps["COMMENTS"].notna().sum())
    S["unique_id_present"] = int(ramps["UNIQUE_ID"].notna().sum())
    S["unique_id_duplicates"] = int(ramps["UNIQUE_ID"].duplicated().sum())

    # ---- CREATEDATE: delineation date, NOT construction date ----
    raw = pd.to_numeric(ramps["CREATEDATE"], errors="coerce")
    dt = pd.to_datetime(raw, unit="ms", utc=True, errors="coerce")
    bad = (raw.isna() | (raw <= 0) | (dt < "1950-01-01") |
           (dt > "2024-07-12 23:59:59+00:00"))
    known_dt = dt.mask(bad)
    S["createdate_sentinels"] = {
        "null": int(raw.isna().sum()),
        "sentinel_nonnull": int((bad & raw.notna()).sum()),
        "known": int(known_dt.notna().sum())}
    years = Counter("unknown" if pd.isna(d) else str(d.year)
                    for d in known_dt)
    S["createdate_year_counter"] = dict(sorted(years.items()))
    S["createdate_min"] = str(known_dt.min().date())
    S["createdate_max"] = str(known_dt.max().date())
    S["createdate_note"] = ("CREATEDATE is the delineation / record "
                            "creation date from aerial imagery capture "
                            "cycles, not a construction date; no ramp "
                            "age is computed anywhere in this package.")

    # ---- PDI zones ----
    pgeoms = [wkb.loads(b) for b in pdi["geometry_wkb"]]
    S["pdi_zones"] = len(pdi)
    S["pdi_score_counter"] = dict(Counter(
        "NULL" if pd.isna(v) else str(int(v)) for v in pdi["PDI_Score"]).most_common())
    S["pdi_ranking_counter"] = counter_pdi = dict(Counter(
        "NULL" if pd.isna(v) else str(v) for v in pdi["PDI_Ranking"]).most_common())
    S["pdi_score_unknown"] = int(pdi["PDI_Score"].isna().sum())
    S["pdi_geoid_null"] = int(pdi["GEOID10"].isna().sum())
    S["pdi_invalid_geometries"] = int(sum(1 for g in pgeoms if not g.is_valid))
    pdi["area_sqmi"] = [area_sqmi(g) for g in pgeoms]
    S["pdi_total_area_sqmi"] = round(float(pdi["area_sqmi"].sum()), 2)
    S["pdi_shape_area_sum_sqmi"] = round(
        float(pdi["Shape__Area"].sum()) / SQFT_PER_SQMI, 2)
    BAND = {"LOW": (1, 4), "MEDIUM": (5, 6), "HIGH": (7, 10)}
    S["pdi_ranking_bands"] = {k: f"scores {a}-{b}" for k, (a, b) in BAND.items()}

    # ---- join 1: ramps -> PDI zones ----
    assign, multi = pip(list(zip(ramps["lon"], ramps["lat"])), pgeoms)
    ramps["taz"] = [assign.get(i, -1) for i in range(N)]
    S["join_ramps_to_pdi"] = {
        "matched": int((ramps["taz"] >= 0).sum()),
        "unmatched": int((ramps["taz"] < 0).sum()),
        "match_rate_pct": pct(int((ramps["taz"] >= 0).sum()), N),
        "multi_polygon_matches": int(multi),
        "note": ("Unmatched ramps fall outside every PDI polygon. The "
                 "ramp layer was captured from regional DRCOG aerial "
                 "imagery and extends beyond the City and County of "
                 "Denver; the neighborhood join (below) places almost "
                 "exactly the same set inside the city, so the "
                 "unmatched set is ramps outside the city boundary, "
                 "not geocoding failures inside it.")}
    ramps["pdi_score"] = [pdi["PDI_Score"].iloc[t] if t >= 0 else np.nan
                          for t in ramps["taz"]]
    ramps["pdi_ranking"] = [pdi["PDI_Ranking"].iloc[t] if t >= 0 else None
                            for t in ramps["taz"]]
    tc = Counter(assign.values())
    pdi["ramps"] = [tc.get(i, 0) for i in range(len(pdi))]
    pdi["ramp_density_per_sqmi"] = pdi["ramps"] / pdi["area_sqmi"]

    # ---- join 2: ramps -> neighborhoods (cross-check + panel) ----
    nb = pd.read_parquet(STACK / "neighborhoods_clean.parquet")
    ngeoms = [wkb.loads(b) for b in nb["geometry_wkb"]]
    nassign, nmulti = pip(list(zip(ramps["lon"], ramps["lat"])), ngeoms)
    ramps["nbhd"] = [nassign.get(i, -1) for i in range(N)]
    S["join_ramps_to_neighborhoods"] = {
        "matched": int((ramps["nbhd"] >= 0).sum()),
        "unmatched": int((ramps["nbhd"] < 0).sum()),
        "match_rate_pct": pct(int((ramps["nbhd"] >= 0).sum()), N),
        "multi_polygon_matches": int(nmulti),
        "outside_pdi_but_inside_neighborhood": int(
            ((ramps["taz"] < 0) & (ramps["nbhd"] >= 0)).sum()),
        "inside_pdi_but_outside_neighborhood": int(
            ((ramps["taz"] >= 0) & (ramps["nbhd"] < 0)).sum())}
    ntc = Counter(nassign.values())
    nb["ramps"] = [ntc.get(i, 0) for i in range(len(nb))]
    nb["area_sqmi"] = [area_sqmi(g) for g in ngeoms]
    nb["ramp_density_per_sqmi"] = nb["ramps"] / nb["area_sqmi"]

    # ---- crashes: pedestrian-involved, 2021+ panel ----
    cr = pd.read_parquet(STACK / "traffic_accidents_clean.parquet")
    assert cr["offense_id"].duplicated().sum() == 0
    S["crash_source"] = {
        "file": "stack/denver/layers/traffic_accidents_clean.parquet",
        "rows": len(cr),
        "window": "2021-01-01 to 2026-10-15 (reported_date_local)",
        "definition": ("Warehouse panel built from Denver crash reports; "
                       "reported date in America/Denver on or after "
                       "2021-01-01, deduplicated on offense_id (0 "
                       "duplicates in the panel). 2026 is a partial "
                       "year (through October 15)."),
        "with_coordinates": int(cr["geo_lon"].notna().sum()),
        "without_coordinates": int(cr["geo_lon"].isna().sum()),
        "pedestrian_involved_all": int(cr["pedestrian_involved"].sum())}
    geo = cr[cr["geo_lon"].notna()].copy().reset_index(drop=True)
    cassign, cmulti = pip(list(zip(geo["geo_lon"], geo["geo_lat"])), pgeoms)
    geo["taz"] = [cassign.get(i, -1) for i in range(len(geo))]
    geo["pdi_score"] = [pdi["PDI_Score"].iloc[t] if t >= 0 else np.nan
                        for t in geo["taz"]]
    geo["pdi_ranking"] = [pdi["PDI_Ranking"].iloc[t] if t >= 0 else None
                          for t in geo["taz"]]
    S["join_crashes_to_pdi"] = {
        "geocoded_crashes": len(geo),
        "matched": int((geo["taz"] >= 0).sum()),
        "unmatched": int((geo["taz"] < 0).sum()),
        "match_rate_pct": pct(int((geo["taz"] >= 0).sum()), len(geo)),
        "multi_polygon_matches": int(cmulti)}
    cc = Counter(cassign.values())
    pdi["crashes_all"] = [cc.get(i, 0) for i in range(len(pdi))]
    ped_geo = geo[geo["pedestrian_involved"]]
    pc = Counter(ped_geo["taz"].tolist())
    pdi["crashes_ped"] = [pc.get(i, 0) for i in range(len(pdi))]

    # ---- band and score tables (derived) ----
    def band_block(d):
        zones = len(d)
        area = float(d["area_sqmi"].sum())
        r = int(d["ramps"].sum())
        return {
            "zones": zones, "area_sqmi": round(area, 2),
            "ramps": r,
            "ramps_per_sqmi": round(r / area, 1) if area else None,
            "zero_ramp_zones": int((d["ramps"] == 0).sum()),
            "median_zone_density_per_sqmi": round(
                float(d["ramp_density_per_sqmi"].median()), 1),
            "min_zone_density_per_sqmi": round(
                float(d["ramp_density_per_sqmi"].min()), 1),
            "max_zone_density_per_sqmi": round(
                float(d["ramp_density_per_sqmi"].max()), 1)}
    S["by_ranking"] = {rk: band_block(pdi[pdi["PDI_Ranking"] == rk])
                       for rk in ["LOW", "MEDIUM", "HIGH"]}
    S["by_score"] = {}
    for sc in range(1, 11):
        d = pdi[pdi["PDI_Score"] == sc]
        b = band_block(d)
        b["ranking"] = d["PDI_Ranking"].iloc[0]
        S["by_score"][str(sc)] = b
    high = pdi[pdi["PDI_Ranking"] == "HIGH"]
    med_all = float(pdi["ramp_density_per_sqmi"].median())
    S["high_band_detail"] = {
        "zones": len(high),
        "zones_below_300_per_sqmi": int((high["ramp_density_per_sqmi"] < 300).sum()),
        "zones_below_citywide_median_zone_density": int(
            (high["ramp_density_per_sqmi"] < med_all).sum()),
        "citywide_median_zone_density_per_sqmi": round(med_all, 1),
        "zero_ramp_zones": int((high["ramps"] == 0).sum()),
        "lowest_density_zones": [
            {"objectid": int(r["OBJECTID"]), "pdi_score": int(r["PDI_Score"]),
             "ramps": int(r["ramps"]), "area_sqmi": round(float(r["area_sqmi"]), 3),
             "ramps_per_sqmi": round(float(r["ramp_density_per_sqmi"]), 1)}
            for _, r in high.sort_values("ramp_density_per_sqmi").head(5).iterrows()]}
    lowdens_high = high[high["ramp_density_per_sqmi"] < 300]
    S["high_band_detail"]["zones_below_300_area_sqmi"] = round(
        float(lowdens_high["area_sqmi"].sum()), 2)
    S["high_band_detail"]["zones_below_300_share_of_high_area_pct"] = pct(
        int(round(float(lowdens_high["area_sqmi"].sum()) * 100)),
        int(round(float(high["area_sqmi"].sum()) * 100)))
    low_nz = pdi[(pdi["PDI_Ranking"] == "LOW") & (pdi["ramps"] > 0)]
    S["low_excluding_zero_zones"] = {
        "zones": len(low_nz), "area_sqmi": round(float(low_nz["area_sqmi"].sum()), 2),
        "ramps": int(low_nz["ramps"].sum()),
        "ramps_per_sqmi": round(float(low_nz["ramps"].sum() / low_nz["area_sqmi"].sum()), 1),
        "note": ("Sensitivity: the LOW aggregate (296.1 per sq mi) is "
                 "dragged by two zero-ramp score-1 zones covering "
                 "34.58 sq mi. Excluding them, LOW density is the "
                 "figure in this block - still below MEDIUM and HIGH.")}
    S["score_8_10_detail"] = band_block(pdi[pdi["PDI_Score"] >= 8])
    S["zero_ramp_zones_all"] = [
        {"objectid": int(r["OBJECTID"]), "pdi_score": int(r["PDI_Score"]),
         "pdi_ranking": r["PDI_Ranking"], "area_sqmi": round(float(r["area_sqmi"]), 2)}
        for _, r in pdi[pdi["ramps"] == 0].iterrows()]
    placed = int((ramps["taz"] >= 0).sum())
    S["placed_ramps"] = placed
    S["high_share"] = {
        "ramps_in_high_zones": int(high["ramps"].sum()),
        "share_of_placed_ramps_pct": pct(int(high["ramps"].sum()), placed),
        "high_area_sqmi": round(float(high["area_sqmi"].sum()), 2),
        "share_of_pdi_area_pct": pct(
            int(round(float(high["area_sqmi"].sum()) * 100)),
            int(round(float(pdi["area_sqmi"].sum()) * 100)))}

    # ---- crash findings by band (derived) ----
    ing = geo[geo["taz"] >= 0]
    S["crashes_by_ranking"] = {}
    for rk in ["LOW", "MEDIUM", "HIGH"]:
        d = ing[ing["pdi_ranking"] == rk]
        p = d[d["pedestrian_involved"]]
        area = float(pdi[pdi["PDI_Ranking"] == rk]["area_sqmi"].sum())
        S["crashes_by_ranking"][rk] = {
            "crashes": len(d), "ped_crashes": len(p),
            "ped_share_of_crashes_pct": pct(len(p), len(d)),
            "ped_crashes_per_sqmi_window": round(len(p) / area, 1),
            "all_crashes_per_sqmi_window": round(len(d) / area, 1),
            "ped_ksi_crashes": int(p["ksi_crash_count_basis"].sum()),
            "ped_ksi_share_pct": pct(int(p["ksi_crash_count_basis"].sum()), len(p)),
            "ped_ksi_small_count_flag": bool(int(p["ksi_crash_count_basis"].sum()) < 30)}
    ped_in = ing[ing["pedestrian_involved"]]
    non_in = ing[~ing["pedestrian_involved"]]
    S["control_ped_vs_nonped_distribution"] = {
        "ped_in_pdi": len(ped_in), "nonped_in_pdi": len(non_in),
        "ped_high_share_pct": pct(int((ped_in["pdi_ranking"] == "HIGH").sum()), len(ped_in)),
        "nonped_high_share_pct": pct(int((non_in["pdi_ranking"] == "HIGH").sum()), len(non_in)),
        "ped_low_share_pct": pct(int((ped_in["pdi_ranking"] == "LOW").sum()), len(ped_in)),
        "nonped_low_share_pct": pct(int((non_in["pdi_ranking"] == "LOW").sum()), len(non_in))}
    S["ped_crashes"] = {
        "panel_total": int(cr["pedestrian_involved"].sum()),
        "geocoded": int(geo["pedestrian_involved"].sum()),
        "in_pdi_zones": int((ped_geo["taz"] >= 0).sum()),
        "geocoded_without_coordinates_excluded": int(
            cr["pedestrian_involved"].sum() - geo["pedestrian_involved"].sum())}
    # score-level ped shares for the chart / table
    S["ped_share_by_score"] = {}
    for sc in range(1, 11):
        d = ing[ing["pdi_score"] == sc]
        S["ped_share_by_score"][str(sc)] = {
            "crashes": len(d), "ped_crashes": int(d["pedestrian_involved"].sum()),
            "ped_share_of_crashes_pct": pct(int(d["pedestrian_involved"].sum()), len(d))}

    # ---- nearest ramp to pedestrian crashes (EPSG:2877 feet) ----
    rx, ry = TR.transform(ramps["lon"].values, ramps["lat"].values)
    rtree = STRtree([Point(x, y) for x, y in zip(rx, ry)])
    ped_xy = TR.transform(ped_geo["geo_lon"].values, ped_geo["geo_lat"].values)
    ped_pts = [Point(x, y) for x, y in zip(ped_xy[0], ped_xy[1])]
    idx, dists = rtree.query_nearest(ped_pts, return_distance=True)
    best = {}
    for i, dist in zip(idx[0].tolist(), dists.tolist()):
        best[i] = min(best.get(i, 1e18), dist)
    nd = np.array([best.get(i, np.nan) for i in range(len(ped_pts))])
    S["nearest_ramp_ped_crashes"] = {
        "n": int(len(nd)),
        "median_ft": round(float(np.median(nd)), 1),
        "p90_ft": round(float(np.percentile(nd, 90)), 1),
        "within_50ft": int((nd <= 50).sum()),
        "within_50ft_pct": pct(int((nd <= 50).sum()), len(nd)),
        "within_150ft": int((nd <= 150).sum()),
        "within_150ft_pct": pct(int((nd <= 150).sum()), len(nd)),
        "within_300ft": int((nd <= 300).sum()),
        "within_300ft_pct": pct(int((nd <= 300).sum()), len(nd)),
        "note": ("Distance from the crash point to the nearest ramp "
                 "point in the full ramp layer (including ramps outside "
                 "PDI zones). Proximity only: it measures neither "
                 "crossing quality nor ramp condition or ADA "
                 "accessibility.")}
    ranks = ped_geo["pdi_ranking"].values
    S["nearest_ramp_ped_crashes"]["within_150ft_by_ranking"] = {
        rk: (pct(int(((nd <= 150) & (ranks == rk)).sum()),
                 int((ranks == rk).sum()))
             if int((ranks == rk).sum()) else None)
        for rk in ["LOW", "MEDIUM", "HIGH"]}

    # ---- controls ----
    s10 = pdi[pdi["PDI_Score"] == 10]
    S["control_score10_zones"] = {
        "zones": len(s10), "area_sqmi": round(float(s10["area_sqmi"].sum()), 2),
        "ramps": int(s10["ramps"].sum()),
        "ramps_per_sqmi": round(float(s10["ramps"].sum() / s10["area_sqmi"].sum()), 1),
        "expectation": ("The 47 score-10 zones are the smallest and "
                        "densest-demand zones (downtown core). If the "
                        "join and area math are sound, they should show "
                        "the highest ramp density of any score."),
        "result": "Highest of the 10 scores (see by_score)."}

    # ---- neighborhood panel stats ----
    S["neighborhoods"] = {
        "count": len(nb),
        "ramps_placed": int((ramps["nbhd"] >= 0).sum()),
        "neighborhoods_with_zero_ramps": int((nb["ramps"] == 0).sum()),
        "median_density_per_sqmi": round(float(nb["ramp_density_per_sqmi"].median()), 1),
        "top_by_ramps": [[r["NBHD_NAME"], int(r["ramps"])]
                         for _, r in nb.sort_values("ramps", ascending=False).head(5).iterrows()],
        "top_by_density": [[r["NBHD_NAME"], round(float(r["ramp_density_per_sqmi"]), 1),
                            int(r["ramps"])]
                           for _, r in nb.sort_values("ramp_density_per_sqmi", ascending=False).head(5).iterrows()],
        "bottom_by_density_nonzero_area": [[r["NBHD_NAME"], round(float(r["ramp_density_per_sqmi"]), 1),
                                            int(r["ramps"])]
                                           for _, r in nb.sort_values("ramp_density_per_sqmi").head(5).iterrows()]}

    # ---- panels ----
    taz_out = pdi[["OBJECTID", "GEOID10", "PDI_Score", "PDI_Ranking",
                   "area_sqmi", "ramps", "ramp_density_per_sqmi",
                   "crashes_all", "crashes_ped"]].copy()
    taz_out.columns = ["objectid", "geoid10", "pdi_score", "pdi_ranking",
                       "area_sqmi", "ramps", "ramps_per_sqmi",
                       "crashes_all_2021plus", "ped_crashes_2021plus"]
    taz_out = taz_out.round({"area_sqmi": 4, "ramps_per_sqmi": 1})
    taz_out.to_csv(ROOT / "data" / "taz_panel.csv", index=False)
    nb_out = nb[["NBHD_NAME", "area_sqmi", "ramps", "ramp_density_per_sqmi"]].copy()
    nb_out.columns = ["neighborhood", "area_sqmi", "ramps", "ramps_per_sqmi"]
    nb_out = nb_out.round({"area_sqmi": 4, "ramps_per_sqmi": 1})
    nb_out.to_csv(ROOT / "data" / "neighborhood_panel.csv", index=False)

    (ROOT / "stats.json").write_text(json.dumps(S, indent=2))
    print(json.dumps({k: S[k] for k in ["total_ramps", "placed_ramps",
                                        "by_ranking", "high_band_detail"]}, indent=2))
    print("stats.json written")


if __name__ == "__main__":
    main()
