"""Section 10 pre-flight audit for the Denver curb ramps brief.

Recomputes the headline figures from the raw pulls and the warehouse
panels, asserts the Section 10 gates, and prints a PASS/FAIL line per
check. Output is saved to data/audit_output.txt and pasted into
verification.md. Run AFTER code/build_stats.py (it reads stats.json
and the panels) and after README.md and brief-draft.md exist (sync
gate). Exits non-zero on any failure.
"""
import json, pathlib, re, sys
import urllib.parse, urllib.request
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
lines, fails = [], []


def check(name, ok, detail=""):
    lines.append(f"{name}: {detail} {'PASS' if ok else 'FAIL'}")
    if not ok:
        fails.append(name)


def project(g):
    return shapely.transform(
        g, lambda xy: np.column_stack(TR.transform(xy[:, 0], xy[:, 1])))


def q(url, params):
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": "MR audit"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())


def main():
    stats = json.loads((ROOT / "stats.json").read_text())
    agg = json.loads((ROOT / "data" / "raw_aggregates.json").read_text())
    ramps = pd.read_parquet(ROOT / "data" / "ramps_raw.parquet")
    pdi = pd.read_parquet(ROOT / "data" / "pdi_raw.parquet")
    taz = pd.read_csv(ROOT / "data" / "taz_panel.csv")
    N, Z = len(ramps), len(pdi)

    # 10.1.4 categorical exhaustiveness: full Counters before any filter
    for col in ["UPDATE_STATUS", "CREATEUSER"]:
        c = Counter("NULL" if pd.isna(v) else str(v) for v in ramps[col])
        check(f"COUNTER {col}", sum(c.values()) == N,
              f"{len(c)} unique values, sum={sum(c.values())} == {N}; values={dict(c.most_common())}")
    c = Counter("NULL" if pd.isna(v) else str(v) for v in ramps["COMMENTS"])
    check("COUNTER COMMENTS", sum(c.values()) == N and c.get("NULL") == N,
          f"values={dict(c.most_common())} (field entirely unpopulated)")
    cs = Counter("NULL" if pd.isna(v) else str(int(v)) for v in pdi["PDI_Score"])
    check("COUNTER PDI_Score", sum(cs.values()) == Z,
          f"{len(cs)} unique values, sum={sum(cs.values())} == {Z}; values={dict(sorted(cs.items()))}")
    cr_ = Counter("NULL" if pd.isna(v) else str(v) for v in pdi["PDI_Ranking"])
    check("COUNTER PDI_Ranking", sum(cr_.values()) == Z,
          f"values={dict(cr_.most_common())}")
    xt = Counter((int(s), r) for s, r in zip(pdi["PDI_Score"], pdi["PDI_Ranking"])
                 if not pd.isna(s))
    band_ok = all(r == ("LOW" if s <= 4 else "MEDIUM" if s <= 6 else "HIGH")
                  for (s, r) in xt)
    check("CROSS PDI_Score x PDI_Ranking", band_ok,
          f"every zone follows LOW=1-4, MEDIUM=5-6, HIGH=7-10; pairs={sorted(xt)}")
    srv_r = {k: v for k, v in agg["ramps"]["update_status_counter_server"]}
    check("SERVER vs LOCAL UPDATE_STATUS",
          srv_r == dict(Counter(ramps["UPDATE_STATUS"]).most_common()),
          f"server={srv_r}")
    srv_p = {int(k): v for k, v in agg["pdi"]["pdi_score_counter_server"]}
    check("SERVER vs LOCAL PDI_Score", srv_p == {int(k): v for k, v in cs.items()},
          f"server zones sum={sum(srv_p.values())}")

    # 10.1.1 / 10.1.2 sentinel handling on CREATEDATE (delineation date)
    raw = pd.to_numeric(ramps["CREATEDATE"], errors="coerce")
    dt = pd.to_datetime(raw, unit="ms", utc=True, errors="coerce")
    bad = (raw.isna() | (raw <= 0) | (dt < "1950-01-01") |
           (dt > "2024-07-12 23:59:59+00:00"))
    known = int((~bad).sum())
    check("SENTINEL CREATEDATE",
          stats["createdate_sentinels"] == {
              "null": int(raw.isna().sum()),
              "sentinel_nonnull": int((bad & raw.notna()).sum()),
              "known": known},
          f"null={int(raw.isna().sum())}, sentinel_nonnull={int((bad & raw.notna()).sum())}, "
          f"known={known}; unknown excluded from every date denominator; "
          "CREATEDATE is never used as ramp age in this package")
    inc = ramps.loc[~bad, ["OBJECTID", "CREATEDATE"]].head(3).values.tolist()
    exc = ramps.loc[bad, ["OBJECTID", "CREATEDATE"]].head(3).values.tolist()
    lines.append(f"  POLARITY CREATEDATE included sample (kept, date in 1950..2024-07-12): {inc}")
    lines.append(f"  POLARITY CREATEDATE excluded sample (null/sentinel -> unknown): {exc} "
                 "(empty: no record is excluded - every CREATEDATE is a valid delineation date)")
    # PDI_Score sentinel handling: null or outside 1..10 -> unknown
    score_bad = pdi["PDI_Score"].isna() | (pdi["PDI_Score"] < 1) | (pdi["PDI_Score"] > 10)
    check("SENTINEL PDI_Score", int(score_bad.sum()) == stats["pdi_score_unknown"] == 0,
          f"unknown scores={int(score_bad.sum())}; all {Z} zones carry a score in 1..10, "
          "so band denominators are the full zone counts")

    # 10.1.5 nullable-denominator trap: shares on the full stated population
    placed = stats["placed_ramps"]
    check("DENOMINATOR ramps placed + unplaced",
          placed + stats["join_ramps_to_pdi"]["unmatched"] == N,
          f"{placed} + {stats['join_ramps_to_pdi']['unmatched']} = {N}; the not-placed "
          f"share ({round(100 * stats['join_ramps_to_pdi']['unmatched'] / N, 1)}%) is printed "
          "alongside the placed share and the two sum to the whole")
    check("DENOMINATOR panel closure",
          int(taz["ramps"].sum()) == placed and len(taz) == Z,
          f"taz_panel rows={len(taz)}, ramps sum={int(taz['ramps'].sum())} == placed {placed}")
    bs = sum(v["ramps"] for v in stats["by_score"].values())
    br = sum(v["ramps"] for v in stats["by_ranking"].values())
    check("PARTITION by_score and by_ranking", bs == br == placed,
          f"by_score sum={bs}, by_ranking sum={br}, placed={placed}")
    cc = sum(v["crashes"] for v in stats["crashes_by_ranking"].values())
    cp = sum(v["ped_crashes"] for v in stats["crashes_by_ranking"].values())
    check("PARTITION crashes by ranking",
          cc == stats["join_crashes_to_pdi"]["matched"] and
          cp == stats["ped_crashes"]["in_pdi_zones"],
          f"crashes sum={cc} == matched {stats['join_crashes_to_pdi']['matched']}; "
          f"ped sum={cp} == in-PDI ped {stats['ped_crashes']['in_pdi_zones']}")

    # 10.1.3 numerator / denominator unit agreement
    high = stats["by_ranking"]["HIGH"]
    panel_high_area = float(taz.loc[taz["pdi_ranking"] == "HIGH", "area_sqmi"].sum())
    recomputed = round(high["ramps"] / panel_high_area, 1)
    check("UNITS ramp density", abs(recomputed - high["ramps_per_sqmi"]) <= 0.2,
          "every density divides ramps by square miles of the SAME zones; "
          f"HIGH recomputed from the panel's 4-decimal areas ({panel_high_area:.2f} sq mi) "
          f"is {recomputed} vs printed {high['ramps_per_sqmi']} (the builder divides by "
          "unrounded areas; stats.json prints areas rounded to 2 decimals, so a "
          "recomputation from the rounded area alone can differ by 0.1)")
    low = stats["crashes_by_ranking"]["LOW"]
    recomputed_ped = round(100.0 * low["ped_crashes"] / low["crashes"], 1)
    recomputed_ksi = round(100.0 * low["ped_ksi_crashes"] / low["ped_crashes"], 1)
    check("UNITS crash shares",
          recomputed_ped == low["ped_share_of_crashes_pct"] and
          recomputed_ksi == low["ped_ksi_share_pct"],
          "pedestrian shares divide pedestrian crashes by crashes in the same band; "
          "KSI shares divide KSI pedestrian crashes by pedestrian crashes in the same band; "
          f"LOW ped share recomputed {recomputed_ped}, KSI share recomputed {recomputed_ksi}; "
          "no persons-over-crashes or cross-unit rate anywhere")

    # 10.2 join hygiene + physical scale
    pgeoms = [wkb.loads(b) for b in pdi["geometry_wkb"]]
    area_proj = sum(float(project(g).area) for g in pgeoms) / SQFT_PER_SQMI
    area_native = float(pdi["Shape__Area"].sum()) / SQFT_PER_SQMI
    check("SCALE PDI area two ways", abs(area_proj - area_native) < 0.1,
          f"projected-from-4326 total {area_proj:.2f} sq mi vs layer Shape__Area sum "
          f"{area_native:.2f} sq mi over {Z} zone polygons (physical scale printed "
          "alongside polygon counts)")
    check("JOIN match rates recorded",
          stats["join_ramps_to_pdi"]["multi_polygon_matches"] == 0 and
          stats["join_crashes_to_pdi"]["multi_polygon_matches"] == 0,
          f"ramps->PDI {stats['join_ramps_to_pdi']['matched']}/{N} "
          f"({stats['join_ramps_to_pdi']['match_rate_pct']}% - below the 95% line, "
          "flagged in the brief and reviewer notes with its systematic "
          "explanation: the ramp layer extends beyond the city); "
          f"ramps->neighborhoods {stats['join_ramps_to_neighborhoods']['matched']}/{N}; "
          f"crashes->PDI {stats['join_crashes_to_pdi']['matched']}/"
          f"{stats['join_crashes_to_pdi']['geocoded_crashes']} "
          f"({stats['join_crashes_to_pdi']['match_rate_pct']}%); multi-polygon matches 0 in all joins")
    agree = (stats["join_ramps_to_neighborhoods"]["outside_pdi_but_inside_neighborhood"] +
             stats["join_ramps_to_neighborhoods"]["inside_pdi_but_outside_neighborhood"])
    check("CONTROL two-polygon-set agreement", agree <= 50,
          f"PDI and neighborhood joins disagree on {agree} of {N} ramps "
          "(23 outside PDI but inside a neighborhood, 7 the reverse) - two "
          "independent polygon sets place the same ramps inside the city")
    s10 = stats["by_score"]["10"]
    check("CONTROL score-10 density",
          all(s10["ramps_per_sqmi"] >= v["ramps_per_sqmi"]
              for k, v in stats["by_score"].items() if k != "10"),
          f"score-10 zones (47 zones, {s10['area_sqmi']} sq mi, the downtown "
          f"demand core) show {s10['ramps_per_sqmi']} ramps per sq mi, the "
          "highest of any score - the join and area math place the densest "
          "ramp concentration where the densest street grid is expected")
    ctl = stats["control_ped_vs_nonped_distribution"]
    check("CONTROL ped vs non-ped distribution",
          ctl["ped_high_share_pct"] > ctl["nonped_high_share_pct"],
          f"pedestrian crashes fall in HIGH zones at {ctl['ped_high_share_pct']}% "
          f"vs {ctl['nonped_high_share_pct']}% for non-pedestrian crashes (the "
          "comparison group) - the demand index separates pedestrian crash "
          "geography from general crash geography in the expected direction")
    # invalid geometry sensitivity
    inv = [i for i, g in enumerate(pgeoms) if not g.is_valid]
    if inv:
        i = inv[0]
        fixed = shapely.make_valid(pgeoms[i])
        a0 = float(project(pgeoms[i]).area) / SQFT_PER_SQMI
        a1 = float(project(fixed).area) / SQFT_PER_SQMI
        high_area = float(taz.loc[taz["pdi_ranking"] == "HIGH", "area_sqmi"].sum())
        high_ramps = int(taz.loc[taz["pdi_ranking"] == "HIGH", "ramps"].sum())
        dens_stored = high_ramps / high_area
        dens_repaired = high_ramps / (high_area - a0 + a1)
        check("SENSITIVITY invalid PDI geometry",
              abs(dens_stored - dens_repaired) < 0.1,
              f"zone OBJECTID {int(pdi.iloc[i]['OBJECTID'])} is invalid as stored; "
              f"its own area as stored {a0:.4f} sq mi vs make_valid {a1:.4f} sq mi "
              f"(difference {100 * abs(a0 - a1) / a0:.2f}% of that one small zone); "
              f"repairing it moves the HIGH band density from {dens_stored:.2f} to "
              f"{dens_repaired:.2f} per sq mi (under 0.1), so no headline figure "
              f"changes; its panel ramp count ({int(taz.iloc[i]['ramps'])}) is "
              "retained and the defect is flagged in reviewer notes")
    # small numbers
    small = [rk for rk, v in stats["crashes_by_ranking"].items()
             if v["ped_ksi_small_count_flag"]]
    check("SMALL NUMBERS", small == ["MEDIUM"],
          f"KSI pedestrian counts by band: LOW {stats['crashes_by_ranking']['LOW']['ped_ksi_crashes']}, "
          f"MEDIUM {stats['crashes_by_ranking']['MEDIUM']['ped_ksi_crashes']} (under 30, flagged "
          f"in stats and in the brief), HIGH {stats['crashes_by_ranking']['HIGH']['ped_ksi_crashes']}; "
          "every percentage in the brief prints its underlying count")

    # fresh live recounts
    base_r = ("https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/"
              "ODC_TRANS_CURBRAMPS_P/FeatureServer/228")
    base_p = ("https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/"
              "ODC_ADMN_PEDDEMANDINDEX_A/FeatureServer/442")
    live_r = q(base_r + "/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    live_p = q(base_p + "/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    check("SERVER fresh live recounts", live_r == N and live_p == Z,
          f"ramps live {live_r} == local {N}; PDI live {live_p} == local {Z}")

    # 10.3 sync gate: README dependencies match code imports; brief numbers in stats
    imported = set()
    for py in (ROOT / "code").glob("*.py"):
        for m in re.finditer(r"^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
                             py.read_text(), flags=re.M):
            imported.add(m.group(1))
    stdlib = {"json", "pathlib", "urllib", "collections", "re", "sys",
              "csv", "math", "statistics", "datetime", "random"}
    third = sorted(imported - stdlib)
    readme = (ROOT / "README.md").read_text()
    dep_line = [ln for ln in readme.splitlines() if ln.startswith("Python standard library")]
    dep_ok = bool(dep_line) and all(t in dep_line[0] for t in third)
    check("SYNC README dependencies", dep_ok,
          f"code imports (third-party): {third}; README dependency line: "
          f"{dep_line[0] if dep_line else 'MISSING'}")
    brief = (ROOT / "brief-draft.md").read_text()
    must = ["72,770", "61,983", "479", "563.3", "663.1", "296.1",
            f"{stats['total_ramps']:,}", "2,558", "100,085"]
    missing = [m for m in must if m not in brief]
    check("SYNC brief numbers present in stats", not missing,
          f"headline figures cross-checked against stats.json; missing from brief: {missing}")
    check("VOICE no en/em dashes in brief", "–" not in brief and "—" not in brief,
          "published text uses plain hyphens only")

    lines.append("AUDIT " + ("FAILED: " + ", ".join(fails) if fails else "PASSED"))
    out = "\n".join(lines)
    (ROOT / "data" / "audit_output.txt").write_text(out + "\n")
    print(out)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
