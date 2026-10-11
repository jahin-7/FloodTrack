"""Acquire once from CDSE + historical OSM; then run pipeline with staged config."""
import argparse,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from floodtrack.core import load_config,save_json
from floodtrack.acquisition import acquire_satellite,download_osm_snapshot

p=argparse.ArgumentParser()
p.add_argument('--config',default='config/case_study.yaml')
p.add_argument('--force',action='store_true',help='Redownload even if cached')
p.add_argument('--osm-only',action='store_true',help='Only fetch historical OSM; keep satellite files unchanged')
a=p.parse_args();cfg=load_config(root/a.config if not Path(a.config).exists() else a.config)
if cfg['source_mode']!='real':raise ValueError('download_inputs requires source_mode: real')
raw=root/'data/raw'/cfg['name'];osm=root/'data/osm'/f"{cfg['name']}_historical.geojson"
raw.mkdir(parents=True,exist_ok=True);osm.parent.mkdir(parents=True,exist_ok=True)
if not a.osm_only and (a.force or not (raw/'s1_pair.tif').exists() or not (raw/'satellite_provenance.json').exists()):
    print('Acquiring satellite inputs from Copernicus Data Space...')
    acquire_satellite(cfg,raw)
elif not a.osm_only: print('Using existing satellite inputs:',raw)
if a.force or not osm.exists():
    print('Acquiring historical OSM snapshot...')
    if str(cfg['osm_snapshot']) == '2026-08-01':
        from floodtrack.geofabrik import acquire as acquire_geofabrik
        meta=acquire_geofabrik(cfg,osm)
    else:
        meta=download_osm_snapshot(cfg,osm)
    save_json(raw/'osm_provenance.json',meta)
else: print('Using existing historical OSM:',osm)
print('OSM step complete.' if a.osm_only else 'Inputs ready. Use source_mode: staged with EXACT SAME name in your pipeline config.')
