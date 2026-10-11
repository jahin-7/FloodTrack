**2026-10-10 update:** Historical OSM can now be downloaded from the verified pre-event Geofabrik Nepal archive (2026-08-01) with `scripts/download_osm_geofabrik.py`. No ohsome or Overpass is required for the configured case study. See `OSM_GEOFABRIK_GUIDE.md`.

# Kaggle — complete step-by-step runbook (FREE CDSE, NO Earth Engine)

**Goal:** use the entire FloodTrack B source ZIP in Kaggle, retrieve real Sentinel-1/2 + DEM from free **Copernicus Data Space Ecosystem (CDSE)** if Kaggle Internet is enabled, train optional flood segmentation on a separately downloaded approved dataset, create dashboard/reports and ZIP **all files**, not only outputs.

**Important:** This is a runnable starter, not a validated trained solution. Synthetic test fixtures are NOT real Nepal results. The free CDSE general-user service has monthly quotas and requires a **Sentinel Hub OAuth client ID/secret** for Processing API requests. Kaggle Internet/GPU availability depends on account/session permissions.

## Phase K0 — Accounts and settings

1. Download `FloodTrack_B_Full_Project_CDSE.zip` from ChatGPT.
2. Create a free Copernicus account at https://dataspace.copernicus.eu/ . Open the Sentinel Hub dashboard and create an OAuth client (https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html). Save **Client ID** and **Client Secret** privately. **Do not use your account password** as the OAuth secret.
3. In Kaggle, open https://www.kaggle.com/code → **New Notebook**.
4. In notebook settings: enable **Internet** (for CDSE + ohsome) and choose a GPU accelerator if you plan to train the U-Net. CPU works for acquisition/baseline.
5. Open Kaggle **Add-ons → Secrets** (wording may vary). Add secrets named `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET`. Grant notebook access. Do not print secrets.
6. Add the project ZIP as a Kaggle **private Dataset** (Datasets → New Dataset → upload ZIP) and attach that dataset with **Add Input** to the notebook. The input directory is read-only; copy/extract into `/kaggle/working`.

## Phase K1 — Extract the whole ZIP into writable working directory

```python
from pathlib import Path
from zipfile import ZipFile
matches=list(Path('/kaggle/input').rglob('FloodTrack_B_Full_Project_CDSE.zip'))
assert matches, 'Attach your private Kaggle Dataset containing the project ZIP'
with ZipFile(matches[0]) as z:
    z.extractall('/kaggle/working')
ROOT=Path('/kaggle/working/FloodTrack_B_Complete')
assert (ROOT/'README.md').exists()
print('Extracted project:',ROOT)
```

The project includes `notebooks/01_Kaggle_Runbook.ipynb`, which follows this Markdown guide.

## Phase K2 — Install packages and run synthetic offline tests

```python
%cd /kaggle/working/FloodTrack_B_Complete
%pip install -q -r requirements.txt
!python -m pytest -q tests
!python scripts/run_pipeline.py --config config/smoke_test.yaml
```

Expected: offline test suite passes; `outputs/synthetic_training_and_pipeline_smoke/dashboard_map.html` is created. This verifies software only, **not real flood accuracy**.

```python
from IPython.display import IFrame,display
display(IFrame('outputs/synthetic_training_and_pipeline_smoke/dashboard_map.html',width='100%',height=600))
```

## Phase K3 — Load Copernicus credentials without hardcoding

```python
import os
from kaggle_secrets import UserSecretsClient
secrets=UserSecretsClient()
os.environ['CDSE_CLIENT_ID']=secrets.get_secret('CDSE_CLIENT_ID')
os.environ['CDSE_CLIENT_SECRET']=secrets.get_secret('CDSE_CLIENT_SECRET')
assert os.environ['CDSE_CLIENT_ID'] and os.environ['CDSE_CLIENT_SECRET']
print('OAuth secrets loaded (hidden)')
!python scripts/run_pipeline.py --config config/case_study.yaml --cdse-check
```

If `kaggle_secrets` is unavailable, your Kaggle account has not enabled the secret feature. Do not put secrets in the ZIP or public notebook; use Colab as the acquisition environment and Kaggle only for staged processing.

## Phase K4 — Configure real case study

```python
import yaml
cfg_path=Path('config/case_study.yaml')
cfg=yaml.safe_load(cfg_path.read_text())
cfg.update({
 'name':'trishuli_2026_demo_aoi',
 'source_mode':'real',
 'case_event_date':'2026-08-26',
 'osm_snapshot':'2026-07-27',
 'bbox':[85.119,28.150,85.157,28.182],  # EXAMPLE; verify location
 'scale_m':30,
 'lookback_days':30,
 'lookforward_days':25,
 'use_optical':True,
 'use_dem':True,
 'ai_model_path':None,
})
cfg_path.write_text(yaml.safe_dump(cfg,sort_keys=False))
```

The example bbox is small to stay within free synchronous CDSE Processing API limits. It is not a confirmed damage polygon. Choose and verify your actual AOI before submission.

## Phase K5 — Preflight: free STAC metadata discovery

```python
!python scripts/check_cdse_catalog.py --config config/case_study.yaml
```

Expected: two Sentinel-1 GRD VV IW product IDs with **identical relative orbit and orbit pass**, one before and one after the event. If no match, increase lookback/lookforward windows or adjust AOI; never force a mismatched pair.

## Phase K6 — Acquire once using CDSE Processing API + historical OSM

```python
!python scripts/download_inputs.py --config config/case_study.yaml
```

Files written:

```text
data/raw/trishuli_2026_demo_aoi/s1_pair.tif
                              /satellite_provenance.json
                              /s2_ndwi.tif (optional)
                              /copernicus_dem.tif (optional)
                              /osm_provenance.json

data/osm/trishuli_2026_demo_aoi_historical.geojson
```

CDSE handles orthorectification/radiometric correction, exports VV backscatter converted to dB; this is **not** local preprocessing of original multi-GB SAFE. Optional optical scenes may be missing in cloud conditions. The historical OSM snapshot must be **before 26 August 2026**.

**Kaggle Internet blocked?** Run C0–C6 from `COLAB_STEP_BY_STEP.md`, package/download the project ZIP from Colab, upload it as a **private Kaggle Dataset**, and continue with K7. You can also attach a private Kaggle Dataset containing the exact `data/raw/<name>` and `data/osm/<name>_historical.geojson` files; preserve `satellite_provenance.json`.

## Phase K7 — Reuse staged data (avoids spending CDSE quota on reruns)

```python
src=yaml.safe_load(Path('config/case_study.yaml').read_text())
src['source_mode']='staged'
Path('config/staged_example.yaml').write_text(yaml.safe_dump(src,sort_keys=False))
!python scripts/run_pipeline.py --config config/staged_example.yaml
```

View dashboard and computed metrics:

```python
from IPython.display import IFrame,display
out=Path('outputs')/src['name']
print((out/'impact_metrics.json').read_text()[:2500])
display(IFrame(str(out/'dashboard_map.html'),width='100%',height=650))
```

**Caution:** The baseline detects *candidate* flood pixels; intersecting buildings/roads/bridges are *possibly exposed*, not confirmed damaged. The road graph estimates *possible* disconnection and can return `unknown`. The baseline is **not trained AI**.

## Phase K8 — Download approved labeled dataset and train model (optional but needed for segmentation AI)

Recommended Kuro Siwo: https://github.com/Orion-AI-Lab/KuroSiwo . Alternative Sen1Floods11: https://github.com/cloudtostreet/Sen1Floods11 . Read original README, paper and licensing; upload/attach dataset as a private Kaggle Dataset if possible. **Dataset files are not included in the starter ZIP.**

The training adapter expects:

```text
data/training/pairs/SITE_001/pre_vv.tif
                             /post_vv.tif
                             /flood_label.tif
                             ...
data/training/pairs/SITE_002/... etc
```

VV images must be calibrated **dB**, georeferenced and actually paired. Read the original dataset class codes. A dataset with only a post-event image cannot be passed to a pre/post model without legitimate pre-event imagery. Label values `1`/`0` below are **placeholders**, not guaranteed by the dataset:

```python
!python scripts/prepare_training.py --pairs data/training/pairs --out data/training/patches --positive-values 1 --negative-values 0 --patch 128
!python scripts/train_segmentation.py --patches data/training/patches --model models/unet_s1.pt --epochs 10 --batch 8 --val-sites SITE_002
```

Save and report independent held-out site IoU, model hyperparameters and data provenance. For the hackathon AI requirement, evaluate on **unseen Himalayan scenes**, not only patch-level random validation.

## Phase K9 — Apply trained model to the Nepal case

Only after the model has been genuinely trained:

```python
assert Path('models/unet_s1.pt').exists()
src['ai_model_path']='models/unet_s1.pt'
Path('config/staged_example.yaml').write_text(yaml.safe_dump(src,sort_keys=False))
!python scripts/run_pipeline.py --config config/staged_example.yaml
```

Review `raster_metrics.json` detector field to confirm trained U-Net inference.

## Phase K10 — Validate and prepare competition deliverables

1. Inspect satellite VV before/after, predicted flood extent and cloud/no-data coverage.
2. Review historical OSM exposure and `unknown` settlements; no unverified destruction claims.
3. **Freeze your model/thresholds** before retrieving official EMSR927 for validation. Keep official reference maps **only** in `data/reference_validation`, never in training or inference inputs.
4. Read `scripts/validate_against_reference.py --help`; compare semantically matching extent polygons, not damage grades vs water masks.
5. Fill `templates/FINAL_REPORT_TEMPLATE.md` (≤6 pages), `templates/DEMO_VIDEO_SCRIPT.md` (3 min), `templates/SUBMISSION_CHECKLIST.md` and required credits in `docs/SOURCE_LINKS_AND_RULES.md`.
6. Prepare GitHub repo for source + instructions. Do not push private data or OAuth secrets.

## Phase K11 — Create complete ZIP and save it before Kaggle session ends

```python
!python scripts/package_everything.py --out /kaggle/working/FloodTrack_B_All_Files.zip
from zipfile import ZipFile
zip_path=Path('/kaggle/working/FloodTrack_B_All_Files.zip')
with ZipFile(zip_path) as z:
    names=z.namelist()
    print('File count:',len(names),'Archive bytes:',zip_path.stat().st_size)
    for key in ('src/floodtrack/acquisition.py','data/raw/','models/','outputs/','notebooks/'):
        print(key, any(key in name for name in names))
```

Download the ZIP from Kaggle **Output** or use notebook **Save Version** and locate `/kaggle/working/FloodTrack_B_All_Files.zip`. The archive includes all **currently present** raw rasters, historical OSM, training patches, checkpoints, notebooks, source and reports; secrets excluded by packaging script. It does **not** include datasets that you never downloaded/copied. Large source data may exceed Kaggle artifact limits; archive license-compliant data separately if needed.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Internet disabled / STAC connection error | Enable Kaggle Internet, or acquire in Colab and import staged data |
| Missing CDSE secrets | Add both under Kaggle Secrets; allow notebook access; no hardcoding |
| HTTP 401/403 | Check Sentinel Hub OAuth client ID/secret and permissions |
| HTTP 429 | Reduce requests/AOI or wait for free quota reset |
| No same-track S1 pair | Expand date window or change AOI; never compare different tracks |
| `s1_pair.tif` missing in staged mode | Acquire first or upload staged real inputs with matching run name |
| Out of disk | Use smaller AOI, reduce training patches or move large files to Kaggle Dataset |
| GPU not offered | Use CPU baseline; training may be slow without GPU |
| Synthetic results mistaken for real | Check `run_manifest.json` and `satellite_provenance.json` before reporting |

**Official docs:** https://documentation.dataspace.copernicus.eu/Quotas.html ; https://documentation.dataspace.copernicus.eu/APIs/STAC.html ; https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html ; https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html .


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
