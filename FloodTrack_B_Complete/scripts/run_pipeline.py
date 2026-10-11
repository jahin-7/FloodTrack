import argparse,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from floodtrack.core import load_config
from floodtrack.pipeline import run

ap=argparse.ArgumentParser()
ap.add_argument('--config',default='config/smoke_test.yaml')
ap.add_argument('--root',default=str(ROOT))
ap.add_argument('--cdse-check',action='store_true',help='Show credential presence (never print values)')
a=ap.parse_args()
config_path=Path(a.config)
if not config_path.exists():config_path=ROOT/a.config
cfg=load_config(config_path)
if a.cdse_check:
    print('CDSE_CLIENT_ID set:',bool(os.getenv('CDSE_CLIENT_ID')))
    print('CDSE_CLIENT_SECRET set:',bool(os.getenv('CDSE_CLIENT_SECRET')))
else:
    run(cfg,a.root)
