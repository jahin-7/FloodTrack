"""POST-INFERENCE ONLY. Reference maps MUST never be passed to fitting or mapping steps.
Input: manually downloaded official reference flood polygons (GeoJSON) in data/reference_validation.
This script is not run during training, threshold selection, or live predictions.
"""
import sys,argparse,json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union,transform
from pyproj import Transformer
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from floodtrack.core import save_json
from floodtrack.mapping import _utm_epsg
p=argparse.ArgumentParser()
p.add_argument('--prediction',required=True,help='outputs/<run>/flood_extent.geojson')
p.add_argument('--reference',required=True,help='data/reference_validation/..geojson')
p.add_argument('--reference-type',choices=['flood_extent'],required=True,
               help='Only geometry classified as matching flood extent; do not mix building damage grades')
p.add_argument('--no-training-or-tuning-confirmation',action='store_true',required=True,
               help='Confirm comparison is after model/pipeline freeze and is NOT used to select parameters')
a=p.parse_args()
ref=Path(a.reference).resolve()
if not ref.is_relative_to((root/'data/reference_validation').resolve()):
    raise SystemExit('Reference MUST reside within data/reference_validation, isolated from inference')
if not Path(a.prediction).exists():raise SystemExit('Predictions missing; run pipeline first')
def u(path):
    js=json.loads(Path(path).read_text())
    if js.get('type')!='FeatureCollection':raise ValueError('Expected GeoJSON FeatureCollection')
    return unary_union([shape(f['geometry']) for f in js['features'] if f.get('geometry')])
pred=u(a.prediction);reference=u(a.reference)
if pred.is_empty or reference.is_empty:raise SystemExit('Empty polygon set; verify data and labels')
bounds=reference.bounds
utm=Transformer.from_crs('EPSG:4326',f'EPSG:{_utm_epsg(bounds)}',always_xy=True)
pred=transform(utm.transform,pred);reference=transform(utm.transform,reference)
intersection=pred.intersection(reference).area
union=pred.union(reference).area
recall=intersection/reference.area if reference.area else None
precision=intersection/pred.area if pred.area else None
metrics={'polygon_iou':intersection/union if union else None,'spatial_precision':precision,
         'spatial_recall':recall,'posthoc_validation_only':True,
         'warning':'Reference polygons must be exactly comparable extent class, CRS EPSG:4326, same spatial AOI; differing mapping date/resolution affects scores'}
folder=Path(a.prediction).resolve().parent
save_json(folder/'external_reference_validation.json',metrics)
print(json.dumps(metrics,indent=2))
