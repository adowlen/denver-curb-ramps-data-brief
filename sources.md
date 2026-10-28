# Sources - Denver curb ramps brief (2026-10-28)

Every figure in the brief traces to one of the sources below. Derived
figures are labeled derived and state their inputs.

## Curb ramp register (Findings 1, 2, 4, 5, 7, 8)

- Source: City and County of Denver open data, ODC_TRANS_CURBRAMPS_P
  ("curb ramps"), ArcGIS FeatureServer layer 228,
  services1.arcgis.com/zdB7qR0BtYrg0Xpl. Service description:
  "Sidewalk ramps delineated from 2022 aerial imagery." The full
  description adds the capture criteria this brief relies on: ramps
  are compiled in 2D from DRCOG 2022 Denver Regional Aerial
  Photography Project imagery; features were originally delineated
  from 2014 aerial imagery and updated in 2016, 2018, 2020, and 2022;
  "Ramps do not have to be ADA accessible to be captured (imagery
  resolution is not high enough to discern this characteristic)";
  additions include features added based on a larger extent of
  capture, not only truly new features in the built environment.
  UPDATE_STATUS domain (from the layer definition): A = Add,
  M = Modify, NC = No Change.
- Pull: October 28, 2026, full layer with geometry (outSR 4326),
  72,770 records (data/ramps_raw.geojson, data/ramps_raw.parquet;
  pull record in data/pull_log.json; server-side counters in
  data/raw_aggregates.json). Server count and local count equal.
- Service vintage: editingInfo.lastEditDate 1720806330874 =
  July 12, 2024.
- Figures taken directly: total 72,770; UPDATE_STATUS NC 69,986,
  A 2,784, M 0 (server groupBy and local Counter agree);
  CREATEUSER "Kucera" 72,770; COMMENTS null 72,770; UNIQUE_ID present
  72,770 with 0 duplicates; geometry present 72,770; CREATEDATE
  populated 72,770, values July 8, 2015 to February 5, 2024, year
  counter 2015: 54,120, 2016: 10, 2017: 7,391, 2019: 5,527, 2021:
  2,854, 2022: 84, 2023: 2,770, 2024: 14.
- Derived: the percentages on these counts (NC 96.2 percent, A 3.8
  percent, 2015 CREATEDATE share 74.4 percent), each on the full
  stated population of 72,770.

## Pedestrian Demand Index (Findings 3, 4, 5, 6)

- Source: City and County of Denver open data,
  ODC_ADMN_PEDDEMANDINDEX_A ("Pedestrian Demand Index"), ArcGIS
  FeatureServer layer 442 (layer id found in the service JSON),
  services1.arcgis.com/zdB7qR0BtYrg0Xpl. Service description: "This
  dataset estimates the demand for walking in different areas of the
  City and County of Denver based on population and employment
  density." Full description: population density sourced from the
  2020 Census; employment density sourced from LEHD Origin-Destination
  Employment Statistics (LODES) Version 7; the two densities are
  added and grouped into 10 value groupings using the Quantile
  method; groupings are assigned a PDI Score (1-10) displayed by
  Traffic Analysis Zone; results should be considered estimates due
  to geographic problems in the 2010 Census block group base units.
  Copyright: The City and County of Denver.
- Pull: October 28, 2026, full layer with geometry (outSR 4326),
  479 zones (data/pdi_raw.geojson, data/pdi_raw.parquet).
- Service vintage: editingInfo.lastEditDate 1786096866432 =
  August 7, 2026, as reported by the service.
- Figures taken directly: 479 zones; PDI_Score counter (48 zones at
  each score 1-9, 47 at score 10; server groupBy and local Counter
  agree); PDI_Ranking counter (LOW 192, MEDIUM 96, HIGH 191);
  GEOID10 populated on all 479 zones.
- Derived: the ranking-to-score band mapping (LOW = scores 1-4,
  MEDIUM = 5-6, HIGH = 7-10), verified by a server-side groupBy on
  PDI_Score and PDI_Ranking together (every zone follows it), not
  assumed from the field names.
- Derived: zone areas. Polygons projected EPSG:4326 to EPSG:2877,
  area in square feet divided by 27,878,400. Total 154.39 square
  miles, matching the sum of the layer's own Shape__Area field
  (154.39 square miles). Band areas: LOW 102.15, MEDIUM 23.13,
  HIGH 29.12 square miles.

## Ramp-to-demand join (Findings 4 and 5)

- Derived by this brief's point-in-polygon join (lon/lat, first
  matching polygon, no point matched more than one polygon):
  61,983 of 72,770 ramps inside a PDI zone (85.2 percent), 10,787
  outside (14.8 percent, flagged; systematic explanation in
  Finding 4).
- Derived band figures: LOW 30,244 ramps / 102.15 sq mi = 296.1 per
  sq mi; MEDIUM 15,334 / 23.13 = 663.1; HIGH 16,405 / 29.12 = 563.3;
  scores 8-10 subset 8,815 / 16.52 = 533.6. Per-score densities,
  median zone densities (LOW 479.5, MEDIUM 660.2, HIGH 714.0),
  HIGH-band spread (27 of 191 zones below 300 per sq mi, covering
  8.95 sq mi = 30.7 percent of HIGH area; 72 of 191 below the
  citywide median zone density 582.1; lowest HIGH zone OBJECTID 133,
  score 8, 52 ramps, 1.005 sq mi, 51.8 per sq mi), and the two
  zero-ramp zones (OBJECTIDs 475 and 476, both score 1, 30.36 and
  4.22 sq mi) are all in stats.json and data/taz_panel.csv.
- Derived sensitivity: LOW excluding the two zero-ramp zones =
  30,244 ramps / 67.57 sq mi = 447.6 per sq mi.

## Neighborhoods (Findings 4 and 8)

- Source: the city's 78 statistical neighborhood polygons (Machine
  Readable stack layer neighborhoods_clean.parquet, sourced from
  Denver open data). The warehouse file stores geometry in
  EPSG:4326 (verified from coordinate ranges: longitude -105.11 to
  -104.60, latitude 39.61 to 39.91), not State Plane feet.
- Derived: point-in-polygon places 61,999 ramps; cross-join
  disagreement with the PDI join is 30 ramps (23 neighborhood-only,
  7 PDI-only). Per-neighborhood counts, areas, and densities are in
  data/neighborhood_panel.csv: Central Park 5,814 ramps;
  Gateway - Green Valley Ranch 4,589; Montbello 2,056; Whittier
  1,207.6 per sq mi (680 ramps); City Park West 1,192.6 (638);
  North Capitol Hill 1,100.5 (388); Cole 1,099.4 (563); Congress
  Park 1,069.7 (1,101); DIA lowest at 16.5 per sq mi (699 ramps over
  42.36 sq mi); Kennedy 47.0 (33 ramps); median neighborhood density
  556.2 per sq mi; all 78 neighborhoods hold at least one ramp.
- The ACS housing-units stack layer (acs_neighborhood_units.parquet)
  was inspected and not used: no figure in this brief normalizes by
  housing units, and adding it would not support any claim the brief
  makes. The cut is recorded here per the layering admission test.

## Crash fusion (Findings 6 and 7)

- Source: Machine Readable traffic accidents layer
  (stack/denver/layers/traffic_accidents_clean.parquet), built from
  Denver open data crash reports (ODC_CRIME_TRAFFICACCIDENTS5YR_P
  lineage, as built for the 2026-10-18 traffic accidents brief).
- Definition reused from that brief's panel: reported date in
  America/Denver on or after January 1, 2021, deduplicated on
  offense_id (0 duplicates in the panel), through October 15, 2026
  (2026 partial). 106,121 panel reports; 101,770 with coordinates
  (95.9 percent); 4,351 without, excluded from spatial joins only.
- Derived by this brief's joins: crashes inside a PDI zone 100,085
  of 101,770 geocoded (98.3 percent). Pedestrian crashes
  (pedestrian_involved flag): 2,666 in the panel, 2,602 geocoded,
  2,558 inside a PDI zone. By band: LOW 788 of 40,275 crashes
  (2.0 percent), 7.7 per sq mi; MEDIUM 542 of 20,398 (2.7 percent),
  23.4 per sq mi; HIGH 1,228 of 39,412 (3.1 percent), 42.2 per sq mi.
  All crashes per sq mi: LOW 394.3, MEDIUM 882.0, HIGH 1,353.4.
  KSI pedestrian crashes (ksi_crash_count_basis, crash-count basis):
  LOW 44 (5.6 percent of the band's pedestrian crashes), MEDIUM 22
  (4.1 percent, under-30 count flagged), HIGH 53 (4.3 percent).
  Comparison group: HIGH-zone share of pedestrian crashes 48.0
  percent vs 39.2 percent for non-pedestrian crashes; LOW-zone share
  30.8 vs 40.5 percent.
- Derived nearest-ramp distances (EPSG:2877 feet, full ramp layer):
  median 50.6 ft over the 2,602 geocoded pedestrian crashes; within
  50 ft 1,282 (49.3 percent); within 150 ft 2,098 (80.6 percent);
  within 300 ft 2,402 (92.3 percent); 90th percentile 273.4 ft;
  within-150-ft share by crash band: HIGH 86.2, MEDIUM 78.2,
  LOW 73.2 percent.

## Not used as construction or compliance data (deliberate exclusions)

- CREATEDATE: a delineation / record-creation date (Finding 2).
  Never used as a construction date, installation year, or ramp age.
- Ramp presence: a location delineated from imagery. Never used as
  an ADA-accessibility, condition, or crossing-quality finding; the
  service description states imagery cannot discern accessibility.
