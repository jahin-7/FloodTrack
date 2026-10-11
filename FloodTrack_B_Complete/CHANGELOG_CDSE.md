# Change log — CDSE conversion (2026-10-09)

- Removed Earth Engine dependency and authentication from `requirements.txt`, scripts, and runbooks.
- Replaced `src/floodtrack/acquisition.py` satellite acquisition with free CDSE public STAC + authenticated Sentinel Hub Processing API.
- Added strict Sentinel-1 same-relative-orbit/same-pass pre/post scene selection and per-scene processed VV dB GeoTIFF export.
- Added optional CDSE Sentinel-2 L2A NDWI and Copernicus DEM GLO-30 acquisition on the same grid.
- Retained ohsome historical OSM snapshot with pre-event validation.
- Added `scripts/check_cdse_catalog.py` (public metadata preflight) and `scripts/download_inputs.py` (acquire once, cache for staged reruns).
- Rebuilt Kaggle/Colab Jupyter notebooks and complete platform-specific Markdown instructions.
- Updated README, phase plan, sources, technical design, QA and submission templates.
- Added offline mocked CDSE tests; total test suite passes without account/network access.
- Kept original Track B brief, synthetic fixtures, dashboard, reports, model training, validation and whole-project ZIP exporter.

**Scope:** small AOIs via synchronous Processing API. Live CDSE authentication and satellite acquisition require the user's credentials and have not been executed during packaging. No pretrained checkpoint or real Nepal imagery is included by default.
