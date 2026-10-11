"""Configuration and provenance enforcement: hard stops on potential leakage."""
from pathlib import Path
from datetime import date
import json
import os
import yaml

BANNED_INPUT_TERMS = ('EMSR927', 'UNOSAT', 'damage_reference', 'copernicus_ems')
ATTRIBUTIONS = [
    'Contains modified Copernicus Sentinel data 2026.',
    'Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.',
    '© OpenStreetMap contributors.',
]

def load_config(path):
    with open(path, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError('Configuration must be a YAML dictionary')
    xmin, ymin, xmax, ymax = [float(v) for v in cfg['bbox']]
    if not (-180 <= xmin < xmax <= 180 and -90 <= ymin < ymax <= 90):
        raise ValueError('bbox must be [min_lon,min_lat,max_lon,max_lat]')
    if (xmax - xmin) * (ymax - ymin) > .2:
        raise ValueError('Small-area synchronous CDSE Processing API requests only; tile a larger study area first')
    if date.fromisoformat(str(cfg['osm_snapshot'])) >= date.fromisoformat(str(cfg['case_event_date'])):
        raise ValueError('OSM snapshot must be before the event')
    if cfg.get('source_mode') not in ('synthetic', 'real', 'staged'):
        raise ValueError('source_mode must be synthetic, real or staged')
    if any(term.lower() in str(cfg).lower() for term in BANNED_INPUT_TERMS):
        raise ValueError('Reference/validation dataset term appeared in pipeline input configuration')
    return cfg

def save_json(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding='utf-8')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def ensure_dir(path):
    p = Path(path); p.mkdir(parents=True, exist_ok=True); return p


def validate_input_tree(input_root):
    """Prevent importing post-event reference products into the main inference path."""
    input_root = Path(input_root)
    for p in input_root.rglob('*'):
        if any(t.lower() in p.name.lower() for t in BANNED_INPUT_TERMS):
            raise RuntimeError(f'Possible leakage: reference map found under inference inputs: {p}')
