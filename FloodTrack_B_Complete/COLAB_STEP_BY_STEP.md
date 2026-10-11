**2026-10-10 update:** Historical OSM can now be downloaded from the verified pre-event Geofabrik Nepal archive (2026-08-01) with `scripts/download_osm_geofabrik.py`. No ohsome or Overpass is required for the configured case study. See `OSM_GEOFABRIK_GUIDE.md`.

# Google Colab — complete step-by-step runbook (FREE CDSE, NO Earth Engine)

**Read this before running:** This project is a reproducible **starter**, not a trained/validated submission. It includes synthetic sample outputs. Real satellite data requires a **free Copernicus Data Space account** and a **Sentinel Hub OAuth client**. Free CDSE usage has monthly quotas. Training requires a separately downloaded, licensed, correctly converted labeled dataset. The final ZIP contains **everything actually present in the project folder**, not files you have not acquired.

## Phase C0 — Accounts and preparation (5–20 minutes)

1. Download `FloodTrack_B_Full_Project_CDSE.zip` from ChatGPT to your computer.
2. Create a free account at https://dataspace.copernicus.eu/ . **Do not register for Google Earth Engine.**
3. Log in, open the **Sentinel Hub dashboard**, and create an OAuth client as shown at https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html . Save the **Client ID** and **Client Secret** somewhere private. They are not the same as your CDSE login/password.
4. Open https://colab.research.google.com/ → **New Notebook** → **Runtime → Change runtime type → T4 GPU** (if available; CPU is sufficient for acquisition and mapping).
5. In Colab's left sidebar, open **Secrets** (key icon) and create `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET`. Enable notebook access to both. Never paste the values into a shared notebook.
6. Keep at least a few GB of free storage; Colab sessions can expire. Use Drive backup later.

## Phase C1 — Extract the complete project

Upload the ZIP via Colab's Files sidebar, then execute:

```python
from pathlib import Path
from zipfile import ZipFile
ZIP = Path('/content/FloodTrack_B_Full_Project_CDSE.zip')
assert ZIP.exists(), f'Upload {ZIP.name} to /content first'
with ZipFile(ZIP) as z:
    z.extractall('/content')
ROOT = Path('/content/FloodTrack_B_Complete')
assert (ROOT/'README.md').exists(), 'Unexpected ZIP layout'
print('Ready:', ROOT)
```

The ZIP contains two **ready-to-open notebooks**: `notebooks/02_Colab_Runbook.ipynb` and `notebooks/01_Kaggle_Runbook.ipynb`. This Markdown guide is the authoritative explanation.

## Phase C2 — Install dependencies and run the offline smoke test

```python
%cd /content/FloodTrack_B_Complete
%pip install -q -r requirements.txt
!python -m pytest -q tests
!python scripts/run_pipeline.py --config config/smoke_test.yaml
```

**Expected:** test suite passes and `outputs/synthetic_training_and_pipeline_smoke/dashboard_map.html` exists. This is a **synthetic software test**, not a real flood result.

```python
from IPython.display import IFrame, display
display(IFrame('outputs/synthetic_training_and_pipeline_smoke/dashboard_map.html',width='100%',height=600))
```

## Phase C3 — Make CDSE credentials available securely

```python
import os
from google.colab import userdata
os.environ['CDSE_CLIENT_ID'] = userdata.get('CDSE_CLIENT_ID')
os.environ['CDSE_CLIENT_SECRET'] = userdata.get('CDSE_CLIENT_SECRET')
assert os.environ['CDSE_CLIENT_ID'] and os.environ['CDSE_CLIENT_SECRET']
print('CDSE credentials loaded (values hidden)')
!python scripts/run_pipeline.py --config config/case_study.yaml --cdse-check
```

**Never** print token, secret, environment dump or screenshot the secret manager.

## Phase C4 — Set your event and area

Edit `config/case_study.yaml` manually, or run:

```python
import yaml
from pathlib import Path
cfg_path=Path('config/case_study.yaml')
cfg=yaml.safe_load(cfg_path.read_text())
cfg.update({
    'name':'trishuli_2026_demo_aoi',
    'source_mode':'real',
    'case_event_date':'2026-08-26',
    'osm_snapshot':'2026-07-27',
    'bbox':[85.119,28.150,85.157,28.182],  # illustrative; VERIFY this AOI
    'scale_m':30,
    'lookback_days':30,
    'lookforward_days':25,
    'use_optical':True,
    'use_dem':True,
    'ai_model_path':None,
})
cfg_path.write_text(yaml.safe_dump(cfg,sort_keys=False))
print(cfg_path.read_text())
```

The default AOI is a **small demonstration rectangle**, not proof it covers the most affected area. Check on a map before making any case-study claim. `scale_m: 30` is an approximate target resolution. Start small to avoid consuming your free monthly processing quota.

## Phase C5 — Discover the exact radar pair, free metadata only

```python
!python scripts/check_cdse_catalog.py --config config/case_study.yaml
```

**Expected:** two Sentinel-1 product IDs and their dates, **same relative orbit and pass**. If no pair, expand `lookback_days`/`lookforward_days` or change bbox. **Do not bypass orbit validation**. If the STAC service changes metadata schema, check its returned properties and update the parser; never fabricate a match.

## Phase C6 — Download real satellite + pre-event OSM inputs

```python
!python scripts/download_inputs.py --config config/case_study.yaml
```

This uses **CDSE Sentinel Hub Processing API** to export small GeoTIFFs, rather than multi-GB raw SAFE files. It generates:

```text
data/raw/trishuli_2026_demo_aoi/
  s1_pair.tif                # pre/post VV in dB, same grid
  satellite_provenance.json  # product IDs, orbit, time, processing
  s2_ndwi.tif                # optional, only if available
  copernicus_dem.tif         # optional, only if available
  osm_provenance.json

data/osm/trishuli_2026_demo_aoi_historical.geojson
```

**If download fails:** check OAuth client, monthly quota, internet, image availability, STAC metadata, or historic OSM service. There is no automatic substitution with post-event reference maps. A `403` often means permissions/authorization, `429` quota/rate limits, `400` a malformed API request, and missing pair means no matching scenes.

## Phase C7 — Run on cached real data (no repeated CDSE charges)

The staged config **must match** the acquisition `name`, bbox and date:

```python
src=yaml.safe_load(Path('config/case_study.yaml').read_text())
src['source_mode']='staged'
Path('config/staged_example.yaml').write_text(yaml.safe_dump(src,sort_keys=False))
!python scripts/run_pipeline.py --config config/staged_example.yaml
```

Inspect:

```python
from IPython.display import display,IFrame
out=Path('outputs')/src['name']
print((out/'impact_metrics.json').read_text()[:2500])
display(IFrame(str(out/'dashboard_map.html'),width='100%',height=650))
```

**Interpretation:** These are *candidate flooded/exposed areas and possible road disconnections*, not verified damaged buildings or confirmed isolated settlements. The baseline is a threshold method, **not a trained AI segmentation model**.

## Phase C8 — Get a ready-made labeled training dataset (optional but required for segmentation-AI choice)

**Recommended:** Kuro Siwo: https://github.com/Orion-AI-Lab/KuroSiwo . Alternative: Sen1Floods11: https://github.com/cloudtostreet/Sen1Floods11 . Read original README/paper/license and download using its documented procedure. **The datasets are not bundled in the ZIP** and their archive structures are not guaranteed to match our training adapter.

For every geographic site, you must prepare three compatible georeferenced GeoTIFFs:

```text
data/training/pairs/SITE_001/pre_vv.tif
data/training/pairs/SITE_001/post_vv.tif
data/training/pairs/SITE_001/flood_label.tif
... repeat for at least two independent sites ...
```

VV inputs must be in **decibels**, not linear power or RGB. Document source data IDs, preprocessing, label values, nodata and CRS. A labeled *single-image* dataset is **not** automatically a paired temporal dataset. If the chosen dataset lacks a valid pre-event scene, adapt the model architecture and document it rather than fabricating pre imagery.

After confirming the dataset's actual class codes (the `1` and `0` below are **examples only**):

```python
!python scripts/prepare_training.py --pairs data/training/pairs --out data/training/patches --positive-values 1 --negative-values 0 --patch 128
!python scripts/train_segmentation.py --patches data/training/patches --model models/unet_s1.pt --epochs 10 --batch 8 --val-sites SITE_002
```

Inspect `models/unet_s1.training.json` and check the validation site was never used for training. A competition-quality segmentation entry needs evaluation on **genuinely unseen Himalayan scenes**, not just random patches from the same scene.

## Phase C9 — Run the trained model

```python
src['ai_model_path']='models/unet_s1.pt'
Path('config/staged_example.yaml').write_text(yaml.safe_dump(src,sort_keys=False))
!python scripts/run_pipeline.py --config config/staged_example.yaml
```

Do this **only if the model checkpoint exists and has been genuinely trained**. Do not claim AI performance from synthetic outputs or the rule-based baseline.

## Phase C10 — Validation, report, demo and dashboard

1. Inspect `flood_mask.tif` vs `s1_pair.tif` visually; note terrain shadow/layover, permanent water, missed debris and no-data.
2. Inspect `impacts.geojson` and `impact_metrics.json`; classify unconnected/unknown settlements cautiously.
3. **Freeze model and thresholds** before retrieving official EMSR927 data; place any reference polygons **only** in `data/reference_validation`.
4. Use `scripts/validate_against_reference.py --help` to see accepted inputs. Compare **matching extent categories**, never confuse damage grade with flood extent.
5. Open the Folium HTML dashboard or launch `streamlit run dashboard/app.py` locally (Colab Streamlit needs a separate secure tunnel).
6. Fill `templates/FINAL_REPORT_TEMPLATE.md` (maximum six pages), `templates/DEMO_VIDEO_SCRIPT.md` (three minutes) and `templates/SUBMISSION_CHECKLIST.md`. Cite Bountos et al. (2024) if Kuro Siwo used and use exact credits in `docs/SOURCE_LINKS_AND_RULES.md`.

## Phase C11 — Back up to Drive and ZIP **everything**

```python
from google.colab import drive
drive.mount('/content/drive')
!python scripts/package_everything.py --out /content/FloodTrack_B_All_Files.zip
import shutil
shutil.copy2('/content/FloodTrack_B_All_Files.zip',
             '/content/drive/MyDrive/FloodTrack_B_All_Files.zip')
print('Saved complete project archive to Google Drive')
```

**Check before submission:**

```python
from zipfile import ZipFile
with ZipFile('/content/FloodTrack_B_All_Files.zip') as z:
    names=z.namelist()
    print('Files:',len(names),'Bytes:',Path('/content/FloodTrack_B_All_Files.zip').stat().st_size)
    for keyword in ('src/floodtrack/acquisition.py','data/raw/','models/','outputs/','notebooks/'):
        print(keyword, any(keyword in x for x in names))
```

The archive script excludes common secrets. Nevertheless, **do not put credentials in source files or notebooks**, and inspect the archive before sharing. If you want all raw data in the ZIP, you must actually acquire/copy it into `data/` first. Large archives can exceed Colab/Drive limits; a GitHub repo should generally contain source and reproducibility instructions, with licensed large data hosted separately.

## Common failures

| Error | What to do |
|---|---|
| `ModuleNotFoundError` | Run `%pip install -r requirements.txt`; restart runtime if needed |
| Missing `CDSE_CLIENT_ID`/`CDSE_CLIENT_SECRET` | Add both in Colab Secrets, enable access, rerun C3 |
| HTTP 401 / 403 | Recreate/check Sentinel Hub OAuth client; do not use ordinary login credentials |
| HTTP 429 / quota exceeded | Wait for free quota reset or reduce bbox/resolution; do not bypass quotas |
| No same-track Sentinel-1 pair | Expand time window or select different AOI; do not combine mismatched tracks |
| Historic OSM unavailable | Check ohsome service/filter/snapshot; do not use current OSM |
| `s1_pair.tif` missing | Complete C6, then staged run; do not try to run staged before acquisition |
| GPU unavailable | Run baseline on CPU; request GPU only for U-Net training |
| Session ended / files disappeared | Restore the full project ZIP from Drive and continue |

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
