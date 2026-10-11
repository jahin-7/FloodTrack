# Hackathon final technical report (MAXIMUM SIX PAGES)

> **Use true numbers from outputs and held-out evaluation. NEVER copy synthetic test numbers into a real report.** Replace all TODO values, delete placeholder paragraphs, and export as a max-six-page PDF.

## Page 1 — Summary and objective

**Title:** FloodTrack B: Candidate Flood Exposure and Settlement Access Screening from Sentinel and Historical OSM  
**Event:** 26 August 2026 northern Nepal (case study)  
**Inputs:** Sentinel-1 VV, Sentinel-2 when cloud-free, Copernicus GLO-30, 2026-07-27 (or other verified pre-event date) OSM  
**Results summary:** [REAL measured data only, derived metrics and acquisition gap]  
**System boundaries:** Educational prototype; not field-verified emergency decision-making.

## Page 2 — Data provenance / safeguards

Satellite scene names, acquisition UTC timestamps, relative-orbit pass, radar pixel coverage; optical masks; DEM; pre-event OSM timestamp, ODbL, training-only Kuro Siwo identifiers; strict EMSR927 post-hoc quarantine. Include a compact data-provenance table.

## Page 3 — Methodology

SAR pre/post same-track change; optical water index and cloud mask; DEM slope mask; ML U-Net details and actual training set composition; OSM hazard intersection; baseline vs post graph connectedness; deterministic numerically grounded reporting. Add ONE workflow figure.

## Page 4 — Measurements and ML generalization

Real area, affected OSM features, road km, settlement cut-off/unknown. Independent Himalayan holdout event IDs, IoU, F1, precision, recall with confidence/variance where justified. Baseline vs trained U-Net. Representative failure examples.

## Page 5 — EMSR927 and qualitative failure analysis

Compare predictions to official same-class maps **only after training/threshold freeze**. Include class definition, map timestamp/resolution, geographic overlap and post-hoc IoU if semantically legitimate, or qualitative differences if only grading maps exist. Discuss roads/bridges likely false positives.

## Page 6 — Limitations, ethics, reproducibility, references

No minute-ahead glacier-collapse warning; satellite revisit, clouds, radar geometry, partial maps, terrain, unknown off-AOI connectivity, no debris validation, unverified building/road status, processing latency, potential dataset bias. GitHub link, command-line reproduction, attributions below.

**Exact required attributions** (preserve):

- Contains modified Copernicus Sentinel data 2026.
- Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.
- © OpenStreetMap contributors.
- Add Bountos et al. (2024) if Kuro Siwo used, Bonafilia et al. (2020) if Sen1Floods11 used.
- European Union, Copernicus Emergency Management Service data (if official maps are shown).
