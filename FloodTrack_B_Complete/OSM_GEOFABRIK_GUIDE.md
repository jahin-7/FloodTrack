# No-ohsome, no-Overpass OSM acquisition (Colab and Kaggle)

The hackathon requires **pre-event OpenStreetMap** data, not present-day edits. Geofabrik publishes a **2026-08-01** Nepal snapshot (before the 2026-08-26 flood):

- https://download.geofabrik.de/asia/nepal-260801.osm.pbf (~412 MB)
- https://download.geofabrik.de/asia/nepal-260801.osm.pbf.md5
- License: ODbL 1.0; attribution: © OpenStreetMap contributors

In a Colab cell:

```python
!apt-get update -qq && apt-get install -y -qq osmium-tool
%cd /content/FloodTrack_B_Complete
!python scripts/download_osm_geofabrik.py --config config/colab_real.yaml
```

If you used `config/case_study.yaml` instead, pass that filename. `osm_snapshot` must equal `2026-08-01` and `case_event_date` must be later. This downloads the **archived** source, verifies its Geofabrik MD5 checksum, clips the configured bbox, exports a filtered GeoJSON, and writes provenance. The large country PBF is cached outside the project; the small AOI extract and GeoJSON are inside the project ZIP.

The resulting file is `data/osm/<config.name>_historical.geojson`. It is directly compatible with `scripts/run_pipeline.py --config config/colab_staged.yaml` once satellite files exist.

**Important:** The 2026-08-01 OSM snapshot is a genuine historical snapshot, but it is not the exact 2026-07-27 snapshot mentioned in the original brief. It is still pre-event. Verify whether the event organizer requires the exact date rather than any pre-event snapshot. Features outside the AOI or missing from OSM cannot be assumed undamaged or connected. An AOI this small may not contain hospitals or major towns; disconnected-settlement results will therefore be uncertain.

If the country archive is temporarily inaccessible, do not use `nepal-latest.osm.pbf` or current Overpass.
