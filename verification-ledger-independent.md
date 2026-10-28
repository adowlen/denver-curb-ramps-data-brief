# Independent verification ledger - Denver curb ramps brief (2026-10-28)

Verifier method (independent of the builder): standard-library-only
recomputation (code/verify_independent.py; json, collections,
datetime, math, urllib; no pandas, no shapely) from the saved raw
GeoJSON pulls, plus fresh live queries against both ArcGIS services
made during the verification pass itself. The spatial join is
recomputed with the verifier's own ray-casting point-in-polygon over
a uniform grid index - a different implementation from the builder's
shapely STRtree join - and band areas are taken from the PDI layer's
native Shape__Area field rather than the builder's projected
geometry. Output: data/verify_independent_output.json. All 33
checks_vs_builder flags: true.

## Figures: all REPRODUCED, none corrected

| Figure | Builder | Independent | Verdict |
|---|---|---|---|
| Ramp records | 72,770 | 72,770 (stdlib recount; fresh live count 72,770) | REPRODUCED |
| UPDATE_STATUS split | NC 69,986 / A 2,784 | NC 69,986 / A 2,784 (stdlib Counter; fresh live groupBy agrees) | REPRODUCED |
| CREATEUSER | Kucera 72,770 | Kucera 72,770 | REPRODUCED |
| COMMENTS populated | 0 | 0 | REPRODUCED |
| UNIQUE_ID duplicates | 0 | 0 | REPRODUCED |
| CREATEDATE year counter | 2015: 54,120; 2017: 7,391; 2019: 5,527; 2021: 2,854; 2023: 2,770; tails 2016: 10, 2022: 84, 2024: 14 | identical, from the verifier's own epoch-ms parse with its own sentinel rule | REPRODUCED |
| PDI zones | 479 | 479 (fresh live count 479) | REPRODUCED |
| PDI score counter | 48 per score 1-9, 47 at 10 | identical | REPRODUCED |
| PDI ranking counter | LOW 192 / MEDIUM 96 / HIGH 191 | identical (fresh live groupBy agrees) | REPRODUCED |
| Band areas (sq mi) | LOW 102.15 / MEDIUM 23.13 / HIGH 29.12; total 154.39 | Same within 0.15 sq mi from native Shape__Area sums (the verifier's area basis is the layer's own field, the builder's is projected geometry; the two agree) | REPRODUCED |
| Ramps placed in PDI zones | 61,983 | 61,983 (verifier's own ray-casting PIP) | REPRODUCED |
| Ramps by band | LOW 30,244 / MEDIUM 15,334 / HIGH 16,405 | identical | REPRODUCED |
| Densities (ramps per sq mi) | LOW 296.1 / MEDIUM 663.1 / HIGH 563.3 | Same within 1.0 per sq mi on the verifier's independent area basis | REPRODUCED |
| Zero-ramp zones | 2 total, 0 in HIGH | 2 total, 0 in HIGH | REPRODUCED |
| Crash partition | band crashes sum 100,085; band pedestrian crashes sum 2,558 | closure holds against stats.json totals | REPRODUCED (arithmetic; the crash panel is parquet and has no stdlib reader - see reviewer notes) |
| Pedestrian shares by band | 2.0 / 2.7 / 3.1 percent | recomputed from the printed counts | REPRODUCED (arithmetic) |
| Nearest-ramp within-150-ft share | 80.6 percent | recomputed from the printed counts (2,098 of 2,602) | REPRODUCED (arithmetic; the distance computation itself is the builder's, controlled by the band pattern in Finding 7) |

## Traps examined (adversarial pass over source definitions and samples)

- T1 A ramp point is not an ADA finding. The service description
  states ramps do not have to be ADA accessible to be captured and
  imagery cannot discern accessibility. Treatment: the caveat is
  printed in the brief's opening, in Finding 1, and again where
  proximity is reported (Finding 7); no figure is phrased as a
  compliance, condition, or crossing-quality measure.
- T2 CREATEDATE is not a construction date. Its distribution (74.4
  percent of records in a single year, 2015) is the signature of
  delineation cycles, and the service description lists capture
  cycles (2014/2016/2018/2020/2022 imagery) rather than construction
  years. Treatment: Finding 2 reports the distribution and refuses
  the proxy; no age, trend, or new-ramp figure exists in the
  package.
- T3 UPDATE_STATUS "Add" is not "newly built." The service
  description states additions include features added based on a
  larger extent of capture. Treatment: Finding 1 prints the
  definition with the counts and does not convert the 2,784 adds
  into a construction figure.
- T4 The ranking bands are the layer's own, verified, not assumed:
  a server groupBy on PDI_Score and PDI_Ranking together shows LOW
  is exactly scores 1-4, MEDIUM 5-6, HIGH 7-10. The brief also
  prints the scores 8-10 subset (533.6 per sq mi) so the headline
  does not depend on the band choice.
- T5 The unmatched-ramp share (14.8 percent) is above the methods
  flag line. Three independent reads agree on the mechanism: the
  points extend beyond the city boundary; a second polygon set
  (the 78 neighborhoods) places the same set inside the city
  (disagreement 30 points); the layer description records regional
  DRCOG capture. Treatment: Finding 4 prints the rate, the flag,
  and the explanation; all densities use placed ramps only.
- T6 Area-weighted versus median zone densities point in different
  directions for the HIGH band (563.3 area-weighted, below MEDIUM;
  median HIGH zone 714.0, above MEDIUM's 660.2). Treatment:
  Finding 5 prints both, names the mechanism (27 large low-density
  HIGH zones covering 30.7 percent of HIGH area), and the "What
  this might mean" section carries the street-pattern alternative.
  No summary in the package quotes one without the other being in
  the same finding.
- T7 One PDI polygon (OBJECTID 258) is invalid as stored. Its area
  differs by 2.96 percent under a validity repair; the band effect
  is under 0.1 ramps per square mile. Treatment: retained as
  stored, measured, and flagged in the brief's data notes, the
  audit, and the reviewer notes. (An early draft of the brief
  misstated the zone-level difference as "under 1 percent"; the
  audit's sensitivity line caught the discrepancy and the text was
  corrected to 3.0 percent - recorded in verification.md.)
- T8 Neighborhood geometry CRS: the warehouse neighborhoods file
  stores lon/lat (EPSG:4326) despite State Plane being the city's
  native grid - the same trap the traffic signals package hit.
  Verified from coordinate ranges before any join ran; all
  point-in-polygon work was done in lon/lat and areas were computed
  only after an explicit projection to EPSG:2877.
- T9 The PDI service reports a last-edit date of August 7, 2026,
  after the ramp layer's July 12, 2024 vintage and close to this
  pull. The definitions in the current service description match
  the ones recorded when the lead was verified (2020 Census plus
  LODES), and the score/ranking counters are the clean quantile
  pattern the description predicts. Treatment: the vintage is
  printed as the service reports it in Finding 3 and the data
  notes; no figure depends on the PDI layer being older than it is.
- T10 Crash window asymmetry: the panel runs to October 15, 2026,
  so 2026 is a partial year. All crash figures are window totals or
  shares inside the window; nothing is annualized, and the window
  is printed wherever crash figures appear.

No open finding. Every figure in the brief traces to stats.json or
the two panels, all rebuilt and re-audited after the final build,
and the decisive join was reproduced exactly by an independent
implementation.
