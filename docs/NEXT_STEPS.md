# FloodTrack — Priority improvement roadmap

This plan is based on the supplied hackathon Track B brief and the uploaded project snapshot, not a live operational assessment.

## P0 — Make results scientifically defensible (mapping quality 30%, AI 25%, access 20%)

1. **Investigate 0.0 km² main mask.** Compare pre/post S1 VV distributions, the `-2 dB` change and `-15 dB` post-water thresholds, DEM slope mask, and morphology against visual overlays. Print candidate pixel counts before/after each filter. Do not tune against EMSR927.
2. **Separate water and debris.** Radar backscatter loss is not uniquely floodwater in steep mountains. Keep water, terrain-change/debris, and uncertain classes separate with class-specific validation.
3. **Train the chosen AI track correctly.** The uploaded ZIP includes model/training code and probability plots but no reusable trained checkpoint or independent Himalayan validation artifact. Supply permitted training pairs, geographic holdouts, predicted masks and class-wise IoU, recall, precision, Dice plus error examples.
4. **Evaluate against EMSR927 only after freezing methodology.** Document map-class compatibility, sensor dates, boundaries and reference uncertainty. Provide spatial agreement and disagreement maps; do not treat landslide reference labels as water segmentation ground truth.
5. **Audit road network.** Preserve OSM snapshot prior to event. Evaluate how snap distances (100/200/300 m), AOI buffer, overpasses and anchor choice change the number of possible cut-offs. Report `unknown` when no baseline path exists.

## P1 — Make the interactive demonstration judge-ready (reports 15%, usability 10%)

6. Add AOI bounding box/date inputs and a one-click pipeline job with progress and error handling; currently the dashboard is a viewer of completed local runs.
7. Show a *before/after image slider* (spatially registered S1/S2 rasters) and a legend distinguishing water mask vs V1/V2 change vs AI probability. Existing figure gallery is static.
8. Add uncertainty and provenance detail per layer: acquisition times, orbit track, valid-data percentage, cloud mask, DEM availability, OSM snapshot, threshold/model version.
9. Show baseline and post-event graphs side by side; add proposed detour distance/time only if supported by credible road network weights; show uncertainty of unknown nodes.
10. Export one-page reports with clearly separated candidate hazards, exposure counts, unknowns, and uncertainty; verify Nepali language output with a fluent reviewer.

## P2 — Reproducibility and software quality

11. Add one-page architecture diagram and real output screenshots to README (included in the upgrade package).
12. Expand tests beyond 14 offline checks to include morphological edge cases, CRSs, AOI clipping, absent optical data, absent DEM, overpass interpretation, and disconnected baselines.
13. Build reusable, quota-aware, tiled CDSE data acquisition for larger arbitrary areas. Run a second unseen Nepal AOI end to end without copying precomputed inputs.
14. Pin dependencies in a `requirements-lock.txt` and document the exact Python/runtime/GPU version. Keep raw data, proprietary credentials and official reference layers out of public repositories.
15. Record the comparison-to-reference protocol and limitations in the final six-page report; capture the 3-minute demo walkthrough.

## GitHub image source provenance

- `docs/images/satellite_before_after.png` ← `outputs/Syapru_Besi_AOI01/final_submission/figures/satellite_and_screening.png`
- `docs/images/water_probability_diagnostic.png` ← `outputs/Syapru_Besi_AOI01/final_submission/figures/water_model_diagnostic.png`
- `docs/images/ai_water_probability_change.png` ← `outputs/Syapru_Besi_AOI01/ai_results/syapru_ai_comparison.png`

These figures originate from the user-supplied local ZIP; do not present them as field ground truth or official Copernicus validation maps.
