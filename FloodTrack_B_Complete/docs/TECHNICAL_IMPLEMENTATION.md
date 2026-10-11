# Technical implementation — CDSE edition

## Architecture

1. Public CDSE STAC scene search for Sentinel-1 GRD IW VV in user AOI/time window.
2. Pair before/after using same `sat:relative_orbit` and `sat:orbit_state`. Reject if missing metadata or no match.
3. Use CDSE Sentinel Hub OAuth client credentials to request **small-area** orthorectified `GAMMA0_TERRAIN` VV backscatter for each acquisition window (±4 minutes). Evalscript converts linear power to dB; invalid `dataMask` pixels become -9999. Merge single-band TIFFs into a registered two-band `s1_pair.tif`.
4. Optionally query Sentinel-2 L2A, select pre/post candidates, request SCL-cloud-masked NDWI. Optionally request Copernicus DEM GLO-30, same grid.
5. Historical ohsome OSM snapshot at configured pre-event date.
6. `mapping.py` baseline detects backscatter drop + dark water candidates, optional optical cues and DEM slope; trained U-Net may replace baseline if a genuine permitted checkpoint is supplied.
7. OSM geometry overlay estimates exposure. Road graph estimates possible loss of road connectivity, with an explicit `unknown` category.
8. Map, bilingual markdown report, one-page PDF and provenance JSON are generated from computed metrics.

## Important limitations

- Sentinel Hub delivers processed derived imagery, **not original raw SAFE**; the pipeline starts with the original catalogue acquisitions but delegates GRD preprocessing to CDSE.
- Same-track STAC selection is explicit, but Processing API does not pin a STAC product ID. Acquisition windows/pass filters mitigate selection ambiguity; inspect processed scene provenance before high-stakes comparisons.
- Radar flood signal is not a validated debris classifier. Radar shadow, slope, layover, permanent water and cloud conditions can produce false positives/negatives.
- Simple road-graph isolation does not establish real passability; missing roads and AOI truncation create uncertainty.
- API quotas and 2400-pixel dimension cap prevent arbitrary large-area inference without additional tiling and reconciliation.
- `s2_ndwi.tif` and DEM are optional; missing datasets are recorded, not fabricated.
- Training data must be adapted to the exact two-channel **dB** model format; label codes must be inspected and documented. Geographic generalization is not demonstrated by smoke tests.

## Exact commands

```bash
python scripts/check_cdse_catalog.py --config config/case_study.yaml
python scripts/download_inputs.py --config config/case_study.yaml
python scripts/run_pipeline.py --config config/staged_example.yaml
python scripts/package_everything.py --out /content/FloodTrack_B_All_Files.zip
```

## Tests

`pytest -q tests` uses synthetic test fixtures and mocks for CDSE API metadata and GeoTIFF export. It does not make live API requests. Live acquisition must be validated with the user's CDSE account.
