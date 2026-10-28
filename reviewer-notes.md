# Reviewer notes - Denver curb ramps brief (2026-10-28)

Package state: brief-draft.md, stats.json, both panels, and charts
are final and in sync; Section 10 audit PASSED on the final build
(after a two-line fix loop, recorded in verification.md);
independent verification reproduced every decisive figure,
including the spatial join exactly, with zero corrections.
hero.png is ABSENT by design in this build: the parent run
generates it from hero_source/hero-brief.md (headline figure
"563 vs 663"). The package is not publishable until the hero is
composited and inspected against the hero standard. NOT published
in this run (build-only tasking); GitHub publication, catalog
update, and follow_up_log entry are the morning QA run's steps.

## Claims most likely to be challenged

1. The headline inversion (HIGH 563.3 vs MEDIUM 663.1 ramps per
   square mile) is an area-weighted figure, and the median zone
   comparison points the other way (median HIGH zone 714.0 vs
   MEDIUM 660.2). Finding 5 prints both in the same finding, with
   the mechanism (27 low-density HIGH zones covering 30.7 percent
   of HIGH area). If any summary, social copy, or headline detaches
   the area-weighted figure from the median, it overstates the
   finding. The social draft carries both the counts and the
   limits; keep it that way.
2. Land area is not an intersection denominator. The strongest
   alternative explanation (street-grid density, campuses, rail
   yards, large parcels inside HIGH zones) is printed in "What
   this might mean," and the Who can act section asks for the
   per-intersection denominator rather than pretending this brief
   has it. A challenger with street-mile data by zone could
   legitimately shrink the gap; the brief's figures would remain
   correct as area-normalized statements.
3. The 14.8 percent unmatched-ramp share is above the project's
   5 percent flag line. The explanation (ramps outside the city
   boundary in a regionally captured layer) is verified three
   ways and printed in Finding 4, but a reader who stops at the
   match rate will see a flagged join. That is the intended
   behavior of the flag; the package does not hide it.
4. Finding 7 (80.6 percent of pedestrian crashes within 150 feet
   of a ramp) is the figure most likely to be misread as a safety
   statement in either direction. The finding itself prints why
   it cannot be one (both point sets concentrate at intersections
   by construction; ramp condition is unmeasured). If QA is
   uneasy, Finding 7 can be cut without touching any other figure.
5. PDI vintage: the PDI service reports a last-edit date of
   August 7, 2026. If the layer was republished with revised zone
   values at that edit, the brief's figures describe the layer as
   pulled on October 28, 2026, which is what every figure claims.
   The definitions and the quantile counter pattern match the
   service description and the October 22 lead verification.

## Dataset-quality items, and whom they reflect on (Section 11.3)

- The ramp layer carries no accessibility, condition, or crossing
  information at all (COMMENTS null on 72,770 of 72,770 records;
  the schema has no condition field), and its service data has not
  been edited since July 12, 2024, on imagery through 2022. These
  are properties of the City and County of Denver's published
  layer (DOTI subject matter, DenverGIS publication). The brief
  reports them as measured facts and addresses the fix to DOTI and
  the open data program in Who can act. This finding touches a
  named department, so it is flagged here for extra care; the
  brief's language stays at the published record's contents and
  makes no claim about internal tracking or field practice.
- One PDI polygon (OBJECTID 258) is stored with an invalid
  geometry. Measured and immaterial to every figure (band effect
  under 0.1 per square mile); flagged in the data notes and the
  audit rather than silently repaired.

## Checks not completed

- Per-intersection or per-street-mile normalization: impossible
  from the published sources - neither layer carries the
  denominator. This is the brief's governing limit, printed in
  Finding 5 and in What this might mean, and it is the subject of
  a Who can act item rather than a silent gap.
- Crash spatial recomputation by the stdlib verifier: the crash
  panel is parquet, which the standard library cannot read, so
  the verifier checks the crash block by arithmetic closure and
  share recomputation from the printed counts (all pass). The
  builder's crash join carries its own controls: the
  non-pedestrian comparison group (48.0 vs 39.2 percent HIGH
  share), the monotone per-square-mile pattern across bands, and
  a 98.3 percent match rate. The ramp-to-PDI join - the package's
  decisive join - WAS recomputed independently and matched
  exactly.
- Nearest-ramp distances were computed by the builder only
  (EPSG:2877, shapely STRtree); the verifier recomputes the
  printed percentages from the counts. The band pattern of the
  within-150-ft shares (HIGH 86.2, MEDIUM 78.2, LOW 73.2) is
  consistent with the independently verified band densities.
- No field verification of any individual ramp or zone was
  performed; the two zero-ramp zones (OBJECTIDs 475 and 476,
  34.58 sq mi combined) are reported as the layer states them.
  Their size and location pattern is consistent with airfield and
  open land in the far northeast, but the package does not name a
  land use for them because no source in the package establishes
  one. (The DIA neighborhood panel row - 699 ramps over 42.36 sq
  mi - is a different geography and is not used to explain them.)

## Surprises worth knowing

- The density peak sits at score 5 (679.2 per sq mi), in the
  middle of the demand scale, and scores 8 and 9 sit below scores
  3, 5, 6, and 7. The non-monotonic shape, not just the band
  inversion, is the finding.
- UPDATE_STATUS uses only two of its three domain values: no
  record in 72,770 carries "M" (Modify), while 2,784 carry "A"
  (Add) and the rest "No Change" - the 2022 cycle recorded
  additions and no modifications, at least as published.
- Pedestrian KSI share does not rise with demand band (LOW 5.6
  percent is the highest of the three), while pedestrian crash
  concentration rises steeply. The brief reports the severity
  pattern flatly and draws no conclusion from it; the MEDIUM
  count (22) is under the small-numbers line.
- The ramp layer's reach outside Denver is large: 10,787 points
  (14.8 percent) sit outside the city, a regional capture footprint
  similar to the traffic signal layer's "within and near" scope.

## Morning QA addendum (2026-10-28 run)

- Hero composited by the QA run from hero_source/hero-brief.md:
  generated story-scene illustration (wheelchair user and cane
  pedestrian at the unbroken teal near corner; amber far corner with
  a stream of walkers), headline "563 vs 663" and the specified sub
  and source lines composited over a gradient scrim with
  code/hero_composite.py, visually inspected - legible, scene
  intact, both numbers labeled with the same measure (ramps per
  square mile). Hero standard met.
- QA spot-checks against primary sources, live on 2026-10-28:
  server counts ramps 72,770 and PDI zones 479 reproduced exactly;
  UPDATE_STATUS server group-by A 2,784 / NC 69,986 reproduced;
  band densities recomputed from data/taz_panel.csv: HIGH 563.3,
  MEDIUM 663.1, LOW 296.1 (zones 191 / 96 / 192) - all match
  stats.json and the brief.
- README dependency list corrected at QA to include Pillow (used by
  code/hero_composite.py) so the sync gate holds on the final files.
