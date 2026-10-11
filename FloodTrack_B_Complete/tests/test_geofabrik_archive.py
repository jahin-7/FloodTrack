import importlib.util
import json
from pathlib import Path
import pytest

FILE = Path(__file__).resolve().parents[1] / 'scripts/download_osm_geofabrik.py'
spec = importlib.util.spec_from_file_location('geofabrik', FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_dated_archive_before_event():
    mod.check_dates('2026-08-01', '2026-08-26')
    with pytest.raises(ValueError):
        mod.check_dates('2026-09-01', '2026-08-26')
    with pytest.raises(ValueError):
        mod.check_dates('2026-08-01', '2026-07-31')

def test_relevant_geojson_only(tmp_path):
    fc = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {'highway': 'residential', 'name': 'road'}, 'geometry': {'type': 'LineString', 'coordinates': [[85.12,28.15],[85.13,28.16]]}},
        {'type': 'Feature', 'properties': {'amenity': 'restaurant'}, 'geometry': {'type': 'Point', 'coordinates': [85.12,28.15]}},
        {'type': 'Feature', 'properties': {'building': 'yes'}, 'geometry': {'type': 'Polygon', 'coordinates': [[[86,28],[86.01,28],[86.01,28.01],[86,28]]]}},
    ]}
    src, dest = tmp_path/'in.geojson', tmp_path/'out.geojson'
    src.write_text(json.dumps(fc))
    assert mod.filter_osm_geojson(src,dest,[85.119,28.15,85.157,28.182]) == 1
    result = json.loads(dest.read_text())
    assert result['features'][0]['properties']['highway'] == 'residential'
