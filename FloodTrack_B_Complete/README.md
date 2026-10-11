**2026-10-10 update:** Historical OSM can now be downloaded from the verified pre-event Geofabrik Nepal archive (2026-08-01) with `scripts/download_osm_geofabrik.py`. No ohsome or Overpass is required for the configured case study. See `OSM_GEOFABRIK_GUIDE.md`.

# FloodTrack B — Copernicus-only Kaggle + Colab project

**Hackathon:** Multimodal AI Hackathon 2026, Track B — Mapping Flood Damage from Space.

**Google Earth Engine is not required.** This project uses **Copernicus Data Space Ecosystem (CDSE)**: the public STAC catalogue for scene discovery, **Sentinel Hub Processing API** for small-area Sentinel-1/Sentinel-2/DEM GeoTIFF exports, and **ohsome** for **historical pre-event** OpenStreetMap. It is a fully packaged, **runnable starter**, not a pretrained or independently verified Nepal flood solution.

> **Start with `COLAB_STEP_BY_STEP.md` or `KAGGLE_STEP_BY_STEP.md`.** Both guides include exact commands, secrets handling, synthetic smoke test, free Copernicus acquisition, training, model inference, reporting and whole-project ZIP export.

## Project structure

```text
FloodTrack_B_Complete/
  README.md / PHASE_PLAN.md
  COLAB_STEP_BY_STEP.md / KAGGLE_STEP_BY_STEP.md
  notebooks/01_Kaggle_Runbook.ipynb / 02_Colab_Runbook.ipynb
  src/floodtrack/          # CDSE, mapping, ML, reports, visualizations
  scripts/                 # catalogue check, acquire, pipeline, training, ZIP, validation
  config/                  # synthetic, real CDSE and staged configurations
  tests/                   # offline tests, including mocked CDSE acquisition
  docs/                    # brief, source rules, validation and technical design
  templates/               # report, demo and checklist
  data/raw/                # acquired real rasters, synthetic example
  data/osm/                # historical OSM GeoJSON
  data/training/           # user-supplied permitted training datasets
  data/reference_validation/  # OFFLINE post-hoc official validation ONLY
  models/                  # optional trained model weights
  outputs/                 # interactive map, exposure, reports, PDF
```

## Prerequisites

- Free account: https://dataspace.copernicus.eu/ . The CDSE **General User** free tier has **monthly quotas**. No Google Cloud account, Google Earth Engine project or paid subscription required. See https://documentation.dataspace.copernicus.eu/Quotas.html .
- From your CDSE dashboard, create a **Sentinel Hub OAuth client** and obtain a `client_id` and `client_secret`: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html . **These are NOT your ordinary CDSE login/password.**
- Run in Kaggle or Colab with internet enabled; keep credentials in platform secrets, never inside ZIP or GitHub.
- A small bounding box (default demo AOI is illustrative; **verify it covers your target**). The synchronous API path is **not** large-region tiled production infrastructure.

## Fast start: local/synthetic (no account)

```bash
pip install -r requirements.txt
pytest -q tests
python scripts/run_pipeline.py --config config/smoke_test.yaml
# outputs/synthetic_training_and_pipeline_smoke/dashboard_map.html
```

**Synthetic output is only a software test. Do not submit as actual Nepal flood evidence.**

## Real data — once, then staged reruns

1. Edit `config/case_study.yaml`: `bbox`, `case_event_date`, `osm_snapshot`, `scale_m`. Keep OSM snapshot **strictly before** event.
2. Set `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET` in a secret manager/environment.
3. Public catalogue preflight (no credentials needed):

   ```bash
   python scripts/check_cdse_catalog.py --config config/case_study.yaml
   ```

4. Download small-area inputs (uses free CDSE quota):

   ```bash
   python scripts/download_inputs.py --config config/case_study.yaml
   ```

5. Confirm `config/staged_example.yaml` uses the **exact same `name` and bbox** as your acquisition config, then:

   ```bash
   python scripts/run_pipeline.py --config config/staged_example.yaml
   ```

   Staged mode reuses downloaded inputs and **does not spend additional CDSE processing quota**. You may alternatively run the full `source_mode: real` pipeline in one step; that reacquires data each time.

6. Open `outputs/<name>/dashboard_map.html`, `situation_report_en_one_page.pdf`, `impact_metrics.json`, and `run_manifest.json`.

### Satellite processing facts

- **Sentinel-1:** CDSE STAC scene metadata must provide VV, IW, **same relative orbit and same orbit pass** before/after event; selection fails closed if no pair. Sentinel Hub requests are confined to each scene's sensing time ±4 minutes, with pass filter, orthorectification and `GAMMA0_TERRAIN` correction. The evalscript converts linear backscatter to **dB**, with `-9999` for invalid pixels. The GeoTIFF contains **two co-registered bands**, before/after.
- **Sentinel-2 (optional):** pre/post L2A NDWI; SCL masks clouds/shadows/snow. Missing imagery is reported, not invented.
- **Copernicus DEM (optional):** GLO-30 for slope mask. All three raster products use the same requested output bounds/dimensions.
- **Historical OSM:** `ohsome` snapshot from before event; no present-day edits.
- **Provenance:** `data/raw/<name>/satellite_provenance.json` and `osm_provenance.json` preserve dates, orbit, scene IDs and processing details. **Sentinel Hub processed imagery is not raw GRD SAFE.**
- **Caveat:** temporal ±4-minute selection and orbit direction constrain processing but cannot enforce exact STAC product ID via the Process API. For publication-grade pixelwise matching, verify the processed product IDs and geometric registration independently. Mountain layover/shadow can still cause false positives.

## Optional trainable AI (not already trained)

The pipeline includes a two-channel VV before/after PyTorch U-Net, but **you must supply and correctly label approved real training data**. Kuro Siwo: https://github.com/Orion-AI-Lab/KuroSiwo . Check label semantics, dataset license and whether scenes have matching pre/post VV in **dB**. Adapter layout:

```text
data/training/pairs/
  SITE_001/pre_vv.tif
  SITE_001/post_vv.tif
  SITE_001/flood_label.tif
  SITE_002/... etc
```

```bash
# ONLY after verifying the dataset's real label values:
python scripts/prepare_training.py --pairs data/training/pairs --positive-values 1 --negative-values 0
python scripts/train_segmentation.py --patches data/training/patches --epochs 10 --batch 8 --val-sites SITE_002
# Set ai_model_path: models/unet_s1.pt in staged_example.yaml, rerun staged pipeline
```

Use **geographically independent** validation sites. Do not use EMSR927 or any published damage maps to train/tune the model. A threshold baseline is **not** a trained AI submission. Kuro Siwo may require conversion from its original format; the repo does **not** pretend a generic tar file is already compatible.

## Deliverables and constraints

- Interactive map dashboard, one-page English situation report PDF, bilingual markdown reports, candidate flood polygons, infrastructure exposure, road-network disconnection screening.
- GitHub README/source, **maximum six-page** report with limitations, **three-minute** demo video, dataset citations and required attributions, and **post-hoc** comparison to EMSR927 after method freeze.
- This prototype **cannot** certify buildings destroyed, bridges impassable or communities truly cut off; results are exposure **candidates**. It does not yet solve large arbitrary AOI tiling, validated debris segmentation or verified unseen Himalayan performance.
- Contest attributions are in `docs/SOURCE_LINKS_AND_RULES.md`. Do not redistribute training datasets without checking license.

## Export the **entire** working project

```bash
python scripts/package_everything.py --out /content/FloodTrack_B_All_Files.zip
```

The default includes all project files **currently present** (raw satellite inputs, historical OSM, model weights, logs, maps, reports, notebooks, code, configs). It excludes common credential/secret files. **It cannot include training data or real scenes you have not downloaded.** Check your ZIP size and contents before handing in. For GitHub, use source + lightweight examples; keep large data in a separate license-compliant archive.

## Tested vs not tested

Offline tests cover synthetic end-to-end pipeline, CDSE STAC pair logic, payloads, auth failures, mock TIFF acquisition and pagination. **Live CDSE requests have not been executed with your credentials**; the free service can return quota, permissions, or scene-availability errors. Fix these from the notebook troubleshooting guide rather than substituting prohibited data.


## Historical OSM HTTP 403 recovery (October 2026)

The `https://api.ohsome.org/v1/elements/geometry` endpoint is known to return
403 for some/all clients. This project now tries the documented
`/v1/elementsFullHistory/geometry` endpoint and reconstructs the snapshot
using `@validFrom <= snapshot < @validTo` and stable OSM IDs. It **never**
substitutes current Overpass data. The fallback may still fail if the provider
is unavailable, rate-limited, or returns incomplete validity metadata.

**If satellite rasters already downloaded, DO NOT rerun the whole download:**

```bash
python scripts/download_inputs.py --config config/case_study.yaml --osm-only
```

Then create a staged config with the same `name` and `source_mode: staged`,
and run `python scripts/run_pipeline.py --config config/staged_example.yaml`.
The `--osm-only` option preserves satellite rasters and OAuth quota.

If both ohsome endpoints fail, wait or supply a **verified pre-event**
GeoJSON with original road linework (not bounding boxes) and a provenance
record. Do not use today's Overpass data, and do not use a bbox-only
substitute for network connectivity.
