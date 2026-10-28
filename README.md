# Denver Curb Ramps and Pedestrian Demand - a Machine Readable data brief

Across Denver's 479 pedestrian-demand zones, the zones the city rates highest for walking demand (Pedestrian Demand Index HIGH, scores 7-10) hold 563.3 curb ramps per square mile, fewer than the medium-demand zones at 663.1 per square mile, out of 61,983 ramps placed inside the zones. Ramp and demand layers pulled October 28, 2026. A ramp point is a location delineated from aerial imagery, not an ADA-compliance finding.

Part of Machine Readable: https://adowlen.github.io/machine-readable/

## Contents

- brief-draft.md - the brief (publishable text)
- stats.json - every figure used in the brief, produced by code/build_stats.py
- verification.md - Section 10 pre-flight audit record and methods checklist (AUDIT PASSED)
- verification-ledger-independent.md - the independent verifier's recomputation ledger
- reviewer-notes.md - claims most likely challenged, checks not completed, flags
- sources.md - dataset citations and the per-figure source audit
- social-drafts.md - LinkedIn draft (held for a future Friday synthesis under the Friday-only rule; Machine Readable never posts to X)
- hero.png - hero graphic (generated illustration, headline figure composited; added by the parent run from hero_source/hero-brief.md)
- charts/ - chart_density_by_pdi_score.png, chart_ped_crashes_by_band.png, chart_density_by_neighborhood.png
- data/ - ramps_raw.geojson and ramps_raw.parquet (the full ramp pull), pdi_raw.geojson and pdi_raw.parquet (the full PDI pull), taz_panel.csv (per-zone panel), neighborhood_panel.csv, raw_aggregates.json, pull_log.json, audit_output.txt, verify_independent_output.json
- code/ - pull_data.py, build_stats.py, audit_section10.py, verify_independent.py, charts.py, hero_composite.py

## Dependencies (match code imports)

Python standard library; matplotlib; numpy; pandas; Pillow; pyproj; shapely.

## Reuse and citation

Licensed CC-BY-4.0 (see LICENSE). Cite as: Machine Readable, "Denver's curb ramps: density peaks where pedestrian demand is middling" (2026), https://github.com/adowlen/denver-curb-ramps-data-brief
