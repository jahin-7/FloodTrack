"""Public CDSE STAC preflight: same-track pair discovery, no login or download."""
import argparse,sys,json
from pathlib import Path
from datetime import date,timedelta
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from floodtrack.core import load_config
from floodtrack.acquisition import _stac_items,select_same_orbit_pair,_dims

p=argparse.ArgumentParser();p.add_argument('--config',default='config/case_study.yaml');a=p.parse_args()
cfg=load_config(root/a.config if not Path(a.config).exists() else a.config)
evt=date.fromisoformat(str(cfg['case_event_date']))
items=_stac_items('sentinel-1-grd',cfg['bbox'],
    (evt-timedelta(days=int(cfg.get('lookback_days',30)))).isoformat(),
    (evt+timedelta(days=int(cfg.get('lookforward_days',25)))).isoformat())
print('S1 STAC records:',len(items))
a,b=select_same_orbit_pair(items,evt)
print(json.dumps({'pre_id':a['id'],'post_id':b['id'],'pre_utc':a['utc'],
 'post_utc':b['utc'],'relative_orbit':a['relative_orbit'],'pass':a['orbit_pass'],
 'pixels_width_height':_dims(cfg['bbox'],cfg.get('scale_m',30))},indent=2))
