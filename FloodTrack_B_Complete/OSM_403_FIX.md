# Fix: ohsome 403 / Overpass timeouts

The ohsome v1 `/elements/geometry` endpoint has a documented HTTP 403
regression (https://github.com/GIScience/ohsome-api/issues/346).

## Existing Colab project (preserve real satellite inputs)

1. Upload the patched ZIP to `/content/FloodTrack_B_Full_Project_CDSE_OSM_FIX.zip`.
2. Extract over the existing `/content/FloodTrack_B_Complete` directory.
   This updates code without deleting additional downloaded satellite data.
3. In a new cell run:

```python
from zipfile import ZipFile
with ZipFile('/content/FloodTrack_B_Full_Project_CDSE_OSM_FIX.zip') as z:
    z.extractall('/content')
%cd /content/FloodTrack_B_Complete
!python -m pytest -q tests/test_osm_history_fallback.py
!python scripts/download_inputs.py --config config/case_study.yaml --osm-only
```

4. Once historical OSM is saved, use the existing staged-mode cell.

## How the fallback works

1. Request pre-event snapshot from `/v1/elements/geometry`.
2. On HTTP 403 and selected transient errors, request a short window from
   `/v1/elementsFullHistory/geometry`.
3. Select OSM versions active **at** the configured pre-event timestamp using
   `@validFrom` and `@validTo`.
4. Reject missing validity fields and empty/invalid outputs.
5. Preserve line geometries for road-network analysis.

**Limitations:** This fallback has been tested using mocked API responses;
live service availability cannot be guaranteed. If both endpoints fail, do not
use current Overpass data, because the challenge disallows post-event OSM edits.
Instead retry later or provide a verified historical OSM GeoJSON.
