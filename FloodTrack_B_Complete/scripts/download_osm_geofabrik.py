"""CLI: download Geofabrik 2026-08-01 Nepal archive, clip AOI, export historical GeoJSON."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from floodtrack.core import load_config,save_json
from floodtrack.geofabrik import acquire, check_dates, filter_osm_geojson, ARCHIVE_URL, ARCHIVE_DATE

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--config',default='config/case_study.yaml')
    p.add_argument('--cache-dir',default=None)
    a=p.parse_args()
    cfg_path=Path(a.config)
    cfg=load_config(cfg_path if cfg_path.exists() else ROOT/cfg_path)
    dest=ROOT/'data/osm'/(cfg['name']+'_historical.geojson')
    dest.parent.mkdir(parents=True,exist_ok=True)
    meta=acquire(cfg,dest,a.cache_dir)
    raw=ROOT/'data/raw'/cfg['name']
    raw.mkdir(parents=True,exist_ok=True)
    save_json(raw/'osm_provenance.json',meta)
    print('Historical OSM ready:',dest,'| relevant features:',meta['features'])
