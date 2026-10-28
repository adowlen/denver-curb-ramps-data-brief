# Verification - Denver curb ramps brief (2026-10-28)

## Pre-flight audit

Required before this package was drafted: code/audit_section10.py
recomputes every headline figure from the raw layers and fails loudly
on any mismatch. Output (data/audit_output.txt), run on the final
build:

```
COUNTER UPDATE_STATUS: 2 unique values, sum=72770 == 72770; values={'NC': 69986, 'A': 2784} PASS
COUNTER CREATEUSER: 1 unique values, sum=72770 == 72770; values={'Kucera': 72770} PASS
COUNTER COMMENTS: values={'NULL': 72770} (field entirely unpopulated) PASS
COUNTER PDI_Score: 10 unique values, sum=479 == 479; values={'1': 48, '10': 47, '2': 48, '3': 48, '4': 48, '5': 48, '6': 48, '7': 48, '8': 48, '9': 48} PASS
COUNTER PDI_Ranking: values={'LOW': 192, 'HIGH': 191, 'MEDIUM': 96} PASS
CROSS PDI_Score x PDI_Ranking: every zone follows LOW=1-4, MEDIUM=5-6, HIGH=7-10; pairs=[(1, 'LOW'), (2, 'LOW'), (3, 'LOW'), (4, 'LOW'), (5, 'MEDIUM'), (6, 'MEDIUM'), (7, 'HIGH'), (8, 'HIGH'), (9, 'HIGH'), (10, 'HIGH')] PASS
SERVER vs LOCAL UPDATE_STATUS: server={'NC': 69986, 'A': 2784} PASS
SERVER vs LOCAL PDI_Score: server zones sum=479 PASS
SENTINEL CREATEDATE: null=0, sentinel_nonnull=0, known=72770; unknown excluded from every date denominator; CREATEDATE is never used as ramp age in this package PASS
  POLARITY CREATEDATE included sample (kept, date in 1950..2024-07-12): [[65616, 1707091200000], [65617, 1707091200000], [65618, 1636934400000]]
  POLARITY CREATEDATE excluded sample (null/sentinel -> unknown): [] (empty: no record is excluded - every CREATEDATE is a valid delineation date)
SENTINEL PDI_Score: unknown scores=0; all 479 zones carry a score in 1..10, so band denominators are the full zone counts PASS
DENOMINATOR ramps placed + unplaced: 61983 + 10787 = 72770; the not-placed share (14.8%) is printed alongside the placed share and the two sum to the whole PASS
DENOMINATOR panel closure: taz_panel rows=479, ramps sum=61983 == placed 61983 PASS
PARTITION by_score and by_ranking: by_score sum=61983, by_ranking sum=61983, placed=61983 PASS
PARTITION crashes by ranking: crashes sum=100085 == matched 100085; ped sum=2558 == in-PDI ped 2558 PASS
UNITS ramp density: every density divides ramps by square miles of the SAME zones; HIGH recomputed from the panel's 4-decimal areas (29.12 sq mi) is 563.3 vs printed 563.3 (the builder divides by unrounded areas; stats.json prints areas rounded to 2 decimals, so a recomputation from the rounded area alone can differ by 0.1) PASS
UNITS crash shares: pedestrian shares divide pedestrian crashes by crashes in the same band; KSI shares divide KSI pedestrian crashes by pedestrian crashes in the same band; LOW ped share recomputed 2.0, KSI share recomputed 5.6; no persons-over-crashes or cross-unit rate anywhere PASS
SCALE PDI area two ways: projected-from-4326 total 154.39 sq mi vs layer Shape__Area sum 154.39 sq mi over 479 zone polygons (physical scale printed alongside polygon counts) PASS
JOIN match rates recorded: ramps->PDI 61983/72770 (85.2% - below the 95% line, flagged in the brief and reviewer notes with its systematic explanation: the ramp layer extends beyond the city); ramps->neighborhoods 61999/72770; crashes->PDI 100085/101770 (98.3%); multi-polygon matches 0 in all joins PASS
CONTROL two-polygon-set agreement: PDI and neighborhood joins disagree on 30 of 72770 ramps (23 outside PDI but inside a neighborhood, 7 the reverse) - two independent polygon sets place the same ramps inside the city PASS
CONTROL score-10 density: score-10 zones (47 zones, 0.63 sq mi, the downtown demand core) show 864.9 ramps per sq mi, the highest of any score - the join and area math place the densest ramp concentration where the densest street grid is expected PASS
CONTROL ped vs non-ped distribution: pedestrian crashes fall in HIGH zones at 48.0% vs 39.2% for non-pedestrian crashes (the comparison group) - the demand index separates pedestrian crash geography from general crash geography in the expected direction PASS
SENSITIVITY invalid PDI geometry: zone OBJECTID 258 is invalid as stored; its own area as stored 0.1144 sq mi vs make_valid 0.1110 sq mi (difference 2.96% of that one small zone); repairing it moves the HIGH band density from 563.35 to 563.41 per sq mi (under 0.1), so no headline figure changes; its panel ramp count (19) is retained and the defect is flagged in reviewer notes PASS
SMALL NUMBERS: KSI pedestrian counts by band: LOW 44, MEDIUM 22 (under 30, flagged in stats and in the brief), HIGH 53; every percentage in the brief prints its underlying count PASS
SERVER fresh live recounts: ramps live 72770 == local 72770; PDI live 479 == local 479 PASS
SYNC README dependencies: code imports (third-party): ['matplotlib', 'numpy', 'pandas', 'pyproj', 'shapely']; README dependency line: Python standard library; matplotlib; numpy; pandas; pyproj; shapely. PASS
SYNC brief numbers present in stats: headline figures cross-checked against stats.json; missing from brief: [] PASS
VOICE no en/em dashes in brief: published text uses plain hyphens only PASS
AUDIT PASSED
```

Notes on the audit's history. The first audit run FAILED on two
lines, and both dispositions are recorded here per Section 10.3.3.
(1) UNITS ramp density: the audit recomputed HIGH density from the
rounded area printed in stats.json (29.12 sq mi) and got 563.4
against the builder's 563.3, which divides by the unrounded area.
Verdict: the builder's figure is correct; the audit's recomputation
input was the rounded display value. The check now recomputes from
the panel's 4-decimal areas with the rounding behavior stated in the
line itself. (2) SENSITIVITY invalid geometry: the builder's draft
text claimed the invalid zone's area differed by "under 1 percent"
under a validity repair; the measured difference is 2.96 percent of
that one zone (0.1144 vs 0.1110 sq mi). Verdict: the count and
mechanism in the draft claim were wrong; the brief and these notes
now print 3.0 percent, and the check now tests what matters - the
band-level effect, which is under 0.1 ramps per square mile
(563.35 stored vs 563.41 repaired), so no headline figure changes.
The polarity sample for CREATEDATE shows the first three records in
OBJECTID order in the raw pull's page order as stored in the parquet
(65616-65618 in the audit's frame indexing); the excluded sample is
empty because no CREATEDATE in the layer is null or a sentinel - all
72,770 are valid delineation dates, which is itself recorded.

## Methods checklist

- [x] Count, do not sample: all 72,770 ramp records and all 479 PDI
  zones pulled (server counts equal local counts for both layers;
  pull log in data/pull_log.json).
- [x] Estimand stated: ramp supply per square mile of zone land
  area, by the city's own demand bands, over the zones as published;
  crash geography against the same bands over January 1, 2021 to
  October 15, 2026.
- [x] Base rates and exposure: every comparison is a rate or share
  on a stated denominator (ramps per square mile of the same zones;
  pedestrian crashes divided by crashes in the same band; KSI
  pedestrian crashes divided by pedestrian crashes in the same
  band). No measured pedestrian-volume or traffic-volume denominator
  exists in the sources, and no street-mile or intersection
  denominator is published by zone; the brief states both limits
  prominently (Findings 5 and 6) and implies no causal pattern.
- [x] Direction of causality considered: stated in Finding 6 and in
  What this might mean. Density of population and employment raises
  both the index and exposure, so the crash concentration is
  expected on exposure alone; ramp placement is also endogenous to
  street pattern and program history. No directional claim is made
  in either direction.
- [x] Category and definition changes over the window: the ramp
  layer is a multi-cycle capture (2014-2022 imagery); its own
  description warns that additions include features added from a
  larger capture extent, not only new construction, and the brief
  prints that warning where UPDATE_STATUS is reported (Finding 1)
  and refuses CREATEDATE as a construction or trend measure
  (Finding 2). The PDI is a single published vintage built on 2020
  Census and LODES Version 7 inputs. Crash definitions are the
  2026-10-18 panel's, reused unchanged; 2026 is a partial year
  (through October 15) and is never annualized.
- [x] Exact date range stated: ramp imagery through the 2022
  capture cycle, layer last edited July 12, 2024, pulled
  October 28, 2026; PDI service last edit August 7, 2026 as
  reported; crash window January 1, 2021 to October 15, 2026,
  America/Denver.
- [x] Join match rates: ramps to PDI zones 61,983 of 72,770
  (85.2 percent) - ABOVE the 5 percent unmatched flag line, flagged
  in Finding 4 and the reviewer notes. The unmatched set differs
  systematically and the brief says how: the points lie outside the
  City and County of Denver, verified three ways (point extents
  beyond the city boundary; a second polygon set, the 78
  neighborhoods, places 61,999 and disagrees with the PDI join on
  only 30 points; the layer's own description records regional
  DRCOG imagery capture). No density or crash figure uses an
  unmatched ramp. Ramps to neighborhoods: 61,999 of 72,770
  (85.2 percent), same explanation. Crashes to PDI zones: 100,085
  of 101,770 geocoded reports (98.3 percent); the 4,351 reports
  without coordinates (4.1 percent of the panel) are excluded from
  spatial joins only, including 64 pedestrian crashes, and may
  differ only in geocoding quality, which the brief does not claim
  to test. No point matched more than one polygon in any join.
- [x] Small numbers: every percentage in the brief prints its
  count. The MEDIUM band's KSI pedestrian count (22) is under 30
  and is flagged in stats.json, in Finding 6, and in the audit.
  The smallest band group printed is the 47 score-10 zones,
  reported with their combined area (0.63 sq mi) alongside.
- [x] Official definitions: PDI score, ranking, and their band
  mapping are the layer's own fields, with the mapping verified by
  a server groupBy on both fields rather than assumed. The PDI
  construction (2020 Census population density plus LEHD LODES
  employment density, quantile groupings) is quoted from the
  service description. UPDATE_STATUS meanings are the layer's own
  coded-value domain (A = Add, M = Modify, NC = No Change). KSI
  uses the crash panel's person-count fields on a crash-count
  basis, labeled as such wherever it appears.
- [x] Sentinel handling (Section 10.1.1 and 10.1.2): CREATEDATE
  values that are null, at or before the epoch, before 1950, or
  after the service edit date map to unknown; in this layer there
  are none (0 null, 0 sentinel), recorded with matched-versus-
  excluded samples in the audit. PDI_Score nulls or values outside
  1-10 map to unknown and out of band denominators; there are none
  (all 479 zones scored).
- [x] Nullable-denominator trap (10.1.5): every ramp share uses
  the full stated population (placed 61,983 plus unplaced 10,787
  equals the full 72,770, asserted in the audit, with the unplaced
  share 14.8 percent printed alongside). Band ramp counts partition
  the placed total exactly (by-score and by-ranking sums both
  61,983). Crash band counts partition the matched total exactly
  (100,085 crashes; 2,558 pedestrian crashes).
- [x] Layering test: stated per layer in the brief's data notes
  and in each finding - the PDI layer makes the demand comparison
  (Finding 5) possible; the crash layer makes the outcome check
  and the non-pedestrian comparison group (Finding 6) possible;
  the neighborhood layer makes the boundary cross-check and the
  named-place panel (Findings 4 and 8) possible. The ACS
  housing-units layer was inspected and cut (no claim needed it);
  the cut is recorded in sources.md.
- [x] Sync gate (10.3): README dependency list matches the code's
  actual imports (compiled from a scan of code/: matplotlib, numpy,
  pandas, pyproj, shapely, plus the standard library; no requests,
  no geopandas, no Pillow). Every headline number in brief-draft.md
  was cross-checked against stats.json programmatically in the
  audit (72,770; 61,983; 479; 563.3; 663.1; 296.1; 2,558; 100,085)
  and by the builder's grep pass over the remaining figures:
  69,986 / 2,784 / 96.2 / 3.8 percent; CREATEDATE years 54,120 /
  7,391 / 5,527 / 2,854 / 2,770; band areas 102.15 / 23.13 / 29.12;
  16,405 / 30,244 / 15,334; scores 8-10 subset 8,815 / 16.52 /
  533.6; medians 479.5 / 660.2 / 714.0 / 582.1; 27 zones / 8.95 sq
  mi / 30.7 percent; OBJECTID 133 at 51.8; zero zones 475 / 476 at
  30.36 / 4.22 sq mi; LOW sensitivity 447.6; crashes 106,121 /
  101,770 / 4,351; band ped shares 2.0 / 2.7 / 3.1 and per-sq-mi
  7.7 / 23.4 / 42.2; all-crash per-sq-mi 394.3 / 882.0 / 1,353.4;
  KSI 44 / 22 / 53 at 5.6 / 4.1 / 4.3 percent; control 48.0 vs
  39.2 percent; nearest-ramp median 50.6 ft, 49.3 / 80.6 / 92.3
  percent within 50 / 150 / 300 ft, 90th percentile 273.4 ft;
  neighborhoods Central Park 5,814, Gateway - Green Valley Ranch
  4,589, Montbello 2,056, Whittier 1,207.6, DIA 16.5.

## Section 11 status/fix loop

Builder: this run (package assembled October 28, 2026).
Independent verifier: separate standard-library-only implementation
(code/verify_independent.py) with its own ray-casting
point-in-polygon, its own area figures from the layer's native
Shape__Area field, and its own live queries; see
verification-ledger-independent.md. All 33 checks reproduced, none
corrected, including an exact reproduction of the spatial join
(61,983 placed; band counts 30,244 / 15,334 / 16,405).
Adversarial pass over definitions: the traps that matter are
disclosed in the brief itself - a ramp point is not an ADA finding
(standing caveat, Findings 1 and 7); CREATEDATE is a delineation
date, not construction (Finding 2); UPDATE_STATUS "Add" includes
capture-extent additions, not only new ramps (Finding 1); the
area-weighted versus median-zone contrast is printed inside
Finding 5 rather than resolved silently; the PDI service's
August 7, 2026 last-edit date is reported as the service states it.
Fix loop: the audit's first run failed two lines; both were
adjudicated (count, mechanism, treatment) and closed on evidence -
see the notes under the audit output above. The charts were
visually inspected after rendering; three title/footnote lines
that clipped at the frame edge were shortened and the charts
re-rendered and re-inspected before this record was written.
Freeze: stats.json, both panels, and brief-draft.md are in sync as
of the final audit run; any edit to a figure after this point
requires re-running code/audit_section10.py and
code/verify_independent.py. Hero: hero.png is intentionally absent
in this build (parent run generates it from
hero_source/hero-brief.md); the package is not publishable until
the hero is composited and inspected.
