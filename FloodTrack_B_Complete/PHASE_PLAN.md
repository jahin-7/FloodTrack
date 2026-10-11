**2026-10-10 update:** Historical OSM can now be downloaded from the verified pre-event Geofabrik Nepal archive (2026-08-01) with `scripts/download_osm_geofabrik.py`. No ohsome or Overpass is required for the configured case study. See `OSM_GEOFABRIK_GUIDE.md`.

# Phase plan — FloodTrack B, no Google Earth Engine

**Goal:** reproducible CDSE satellite acquisition → flood-candidate map → historical OSM exposure → potential road isolation → grounded bilingual situation report → optional trained segmentation AI → reference-only evaluation → submission.

## Milestones and completion criteria

| Phase | What you do | Commands / files | Exit criterion |
|---|---|---|---|
| 0. Rules and AOI | Read Track B PDF, select AOI and event date, keep official reference strictly separate | `docs/Track_B_Original_Brief.pdf`, `config/case_study.yaml` | Pre-event OSM date, no forbidden input |
| 1. Environment | Start Colab or Kaggle, install requirements, test synthetic pipeline | `pytest -q tests`; `python scripts/run_pipeline.py --config config/smoke_test.yaml` | Tests pass and synthetic dashboard opens |
| 2. CDSE access | Register free CDSE, create Sentinel Hub OAuth client, save client ID/secret in platform secrets | `CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET` | Both secrets available in session without being printed |
| 3. Scene discovery | Search public CDSE STAC for S1 IW VV and verify same pass/relative orbit | `python scripts/check_cdse_catalog.py --config config/case_study.yaml` | Scene IDs/timestamps/orbit reported; fail if none |
| 4. Acquire real inputs | Use CDSE Process API to export corrected S1 pair, optional S2/DEM; fetch historical OSM | `python scripts/download_inputs.py --config config/case_study.yaml` | GeoTIFFs and provenance + historical GeoJSON exist |
| 5. Baseline | Run staged pipeline, review false positives, inspect timestamps and coverage | `python scripts/run_pipeline.py --config config/staged_example.yaml` | Flood mask, dashboard, impact metrics, reports |
| 6. Model training | Download permitted Kuro Siwo or Sen1Floods11; inspect label schema; adapt to paired dB VV GeoTIFFs; train with site holdout | `scripts/prepare_training.py`, `scripts/train_segmentation.py` | Trained checkpoint and held-out metrics; no EMS leakage |
| 7. AI inference | Set `ai_model_path` in staged config and rerun | `models/unet_s1.pt`, `outputs/<name>` | Detector field names actual checkpoint model |
| 8. Network / QA | Check buildings, bridges, road graph and AOI boundary bias; document uncertainty | `impact_metrics.json`, `impacts.geojson` | Counts/unknowns inspected; not presented as verified destruction |
| 9. Reference validation | Freeze model/thresholds, then compare to matching EMSR927 extent classes only | `scripts/validate_against_reference.py` | Comparison and limitations documented, no tuning |
| 10. Final delivery | Prepare 6-page report, 3-minute demo, GitHub repo, citations, complete ZIP | `templates/`, `scripts/package_everything.py` | Reproducible second small AOI; ZIP includes available inputs, weights and outputs |

## Platform strategy

**Colab:** Recommended for initial setup and CDSE OAuth. Save project and real inputs to Drive before session expiry. Use notebook `notebooks/02_Colab_Runbook.ipynb`.

**Kaggle:** Enable Internet for CDSE requests, GPU for training, add client ID and secret via Kaggle Secrets. If Internet or Secrets unavailable, use staged dataset created in Colab. Use `notebooks/01_Kaggle_Runbook.ipynb`.

## Required acceptance gates

- Same-relative-orbit **and** same-pass S1 pair; otherwise stop rather than mix tracks.
- Output TIFF two-band pre/post calibrated VV in dB; no raw-SAFE misrepresentation.
- Historical OSM snapshot **strictly before** flood; never fall back to current OSM.
- Official Copernicus EMS / UNOSAT maps are **evaluation-only**, never used as predictors or labels.
- Geographic site-level holdout and Himalayan generalization evaluation for trained segmentation.
- Validate second judge-style AOI/date. This starter has **small AOI limits**, so do not claim unlimited AOI support.
- Synthetic maps are labeled synthetic and not represented as actual case-study evidence.
- Complete ZIP contains **everything currently acquired**, but cannot magically contain data never downloaded; check licensing before public redistribution.

## Scoring priorities (from Track B brief)

Flood and damage mapping **30%**; AI component **25%**; cut-off settlements **20%**; reporting/limitations **15%**; dashboard/report usability **10%**.
