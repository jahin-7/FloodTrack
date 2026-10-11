"""Change detection, geospatial exposure, network cut-off (screening, not verified damage)."""
from pathlib import Path
import math
import json
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.features import shapes
from scipy.ndimage import median_filter, binary_opening, binary_closing
from shapely.geometry import shape, mapping, Point, LineString, MultiLineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from pyproj import CRS, Transformer, Geod
import networkx as nx
from .core import save_json

GEOD=Geod(ellps='WGS84')


def _utm_epsg(bbox):
    lon=(bbox[0]+bbox[2])/2; lat=(bbox[1]+bbox[3])/2
    return (32600 if lat>=0 else 32700) + min(60,max(1,int((lon+180)//6)+1))


def read_aligned(path, reference, band=1):
    with rasterio.open(reference) as ref, rasterio.open(path) as src:
        arr=np.zeros((ref.height,ref.width),dtype='float32')
        reproject(source=rasterio.band(src,band),destination=arr,
                  src_transform=src.transform,src_crs=src.crs,
                  dst_transform=ref.transform,dst_crs=ref.crs,
                  src_nodata=src.nodata,dst_nodata=-9999,resampling=Resampling.bilinear)
        return arr


def _slope_degrees(dem, transform, crs):
    # Gradient in meters using local geodetic approximate pixel spacing.
    h,w=dem.shape
    midlon,midlat=rasterio.transform.xy(transform,h//2,w//2)
    dx=abs(transform.a)*111320*max(.1,math.cos(math.radians(midlat)))
    dy=abs(transform.e)*111320
    if crs and not crs.is_geographic:
        dx=abs(transform.a);dy=abs(transform.e)
    gy,gx=np.gradient(dem.astype(float),max(dy,1),max(dx,1))
    return np.degrees(np.arctan(np.hypot(gx,gy)))


def segment(raw_dir, out_dir, cfg):
    raw_dir=Path(raw_dir); out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
    s1=raw_dir/'s1_pair.tif'
    with rasterio.open(s1) as src:
        if src.count!=2:
            raise RuntimeError('s1_pair.tif must have exactly two registered VV bands (pre, post)')
        pre=src.read(1).astype('float32');post=src.read(2).astype('float32')
        valid=np.isfinite(pre)&np.isfinite(post)&(pre>-70)&(post>-70)&(pre<20)&(post<20)
        profile=src.profile.copy(); transform=src.transform;crs=src.crs
    coverage=float(valid.mean())
    if coverage<cfg.get('min_valid_coverage',.70):
        raise RuntimeError(f'S1 AOI valid coverage {coverage:.1%} < required minimum; do not extrapolate missing coverage')
    # Lower backscatter / reduced VV after the event can indicate smooth water, but also radar geometry changes.
    pre_s=median_filter(pre,size=3); post_s=median_filter(post,size=3)
    flood=valid & ((post_s-pre_s)<=float(cfg.get('radar_drop_db',-2))) & (post_s<=float(cfg.get('radar_post_water_db',-15)))
    optical_usable=False; optical_note='not available'
    if (raw_dir/'s2_ndwi.tif').exists():
        b=read_aligned(raw_dir/'s2_ndwi.tif',s1,1)
        a=read_aligned(raw_dir/'s2_ndwi.tif',s1,2)
        good=(b>-5)&(a>-5)&np.isfinite(b)&np.isfinite(a)
        optical_usable=bool(good.any())
        # Independent positive water cue (not mandatory); cloud masked optical pixels never become 0 (=land).
        flood = flood | (valid & good & (a>.15) & ((a-b)>.16))
        optical_note=f'{good.mean():.1%} pixels optical-valid; radar remains primary'
    slope_note='not available'
    if (raw_dir/'copernicus_dem.tif').exists():
        dem=read_aligned(raw_dir/'copernicus_dem.tif',s1,1)
        dem_valid=np.isfinite(dem)&(dem>-9000)
        if dem_valid.any():
            # Nodata is not a physical elevation; fill only for gradient estimation.
            fill=float(np.median(dem[dem_valid]))
            slope=_slope_degrees(np.where(dem_valid,dem,fill),transform,crs)
            # Apply slope filter only where DEM is valid; do not assert an unknown slope.
            flood &= (~dem_valid) | (slope <= float(cfg.get('max_slope_degrees',12.0)))
            slope_note=(f'slope mask applied at <= {cfg.get("max_slope_degrees",12)} degrees '
                        f'where DEM valid ({dem_valid.mean():.1%} coverage)')
        else:
            slope_note='DEM entirely invalid; slope filter not applied'
    flood=binary_closing(binary_opening(flood,iterations=1),iterations=1)&valid
    # Optional learned segmentation model; user must explicitly supply a model trained on permitted source data.
    mode='transparent threshold baseline (NOT a trained AI segmentation model)'
    if cfg.get('ai_model_path'):
        from .train import predict_mask
        ml_mask=predict_mask(cfg['ai_model_path'],pre,post)
        flood=(ml_mask>0.5)&valid
        mode='PyTorch two-channel U-Net (trained checkpoint supplied)'
    profile.update(driver='GTiff',count=1,dtype='uint8',nodata=255,compress='deflate',tiled=False)
    profile.pop('blockxsize',None);profile.pop('blockysize',None)
    mask=np.where(valid,flood.astype('uint8'),255).astype('uint8')
    with rasterio.open(out_dir/'flood_mask.tif','w',**profile) as dst:dst.write(mask,1)
    features=[]
    for g,v in shapes(mask,mask=(mask==1),transform=transform):
        if int(v)==1:
            poly=shape(g)
            if poly.is_valid and not poly.is_empty: features.append(poly)
    if crs and str(crs).upper()!='EPSG:4326':
        tx=Transformer.from_crs(crs,'EPSG:4326',always_xy=True)
        from shapely.ops import transform as shp_transform
        features=[shp_transform(tx.transform,g) for g in features]
    flood_geom=unary_union(features) if features else shape({'type':'GeometryCollection','geometries':[]})
    # UTM area: robust across regional AOIs; world spanning AOIs aren't supported in this prototype.
    xmin,ymin,xmax,ymax=cfg['bbox']
    utm=Transformer.from_crs('EPSG:4326',f'EPSG:{_utm_epsg(cfg["bbox"])}',always_xy=True)
    from shapely.ops import transform as shp_transform
    flood_area_m2=float(shp_transform(utm.transform,flood_geom).area) if not flood_geom.is_empty else 0.0
    geojson={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'source':'derived from Sentinel only'},'geometry':mapping(g)} for g in features]}
    save_json(out_dir/'flood_extent.geojson',geojson)
    met={'area_km2':round(flood_area_m2/1e6,5), 'valid_radar_fraction':round(coverage,4),
         'detector':mode,'optical_note':optical_note,'slope_note':slope_note,
         'pixel_count':int(flood.sum()),'flood_polygon_count':len(features),
         'warning':'water/debris candidate; no independent damage confirmation; terrain shadow and permanent-water false positives possible'}
    save_json(out_dir/'raster_metrics.json',met)
    return flood_geom,met


def _tags(feature):
    props=feature.get('properties') or {}
    tags=props.get('tags')
    return tags if isinstance(tags,dict) else props


def _osm_type(feature):
    tags=_tags(feature)
    return tags


def _iter_lines(geom):
    if isinstance(geom, LineString):yield geom
    elif isinstance(geom, MultiLineString):yield from geom.geoms


def classify_osm(osm_path):
    src=json.loads(Path(osm_path).read_text(encoding='utf-8'))
    out={'buildings':[],'roads':[],'bridges':[],'settlements':[],'hospitals':[]}
    for f in src.get('features',[]):
        if not f.get('geometry'):continue
        try: geom=shape(f['geometry'])
        except Exception:continue
        tags=_tags(f)
        if 'building' in tags and geom.geom_type in ('Polygon','MultiPolygon'):
            out['buildings'].append((geom,tags))
        if 'highway' in tags and geom.geom_type in ('LineString','MultiLineString'):
            out['roads'].append((geom,tags))
            if str(tags.get('bridge','')).lower() not in ('','no','false'):
                out['bridges'].append((geom,tags))
        if 'bridge' in tags and geom.geom_type in ('LineString','MultiLineString') and 'highway' not in tags:
            out['bridges'].append((geom,tags))
        if tags.get('place') in ('city','town','village','hamlet','isolated_dwelling'):
            out['settlements'].append((geom.representative_point(),tags))
        if tags.get('amenity') in ('hospital','clinic') or tags.get('healthcare') in ('hospital','clinic'):
            out['hospitals'].append((geom.representative_point(),tags))
    return out


def _edge_key(p):
    return round(float(p[0]),7),round(float(p[1]),7)


def _road_graph(roads,flood_geom):
    # Unary union nodes line intersections (planar approximation, overpasses may need filtering).
    all_lines=[line for geom,_ in roads for line in _iter_lines(geom) if not line.is_empty]
    if not all_lines:return nx.Graph(), nx.Graph(), []
    noded=unary_union(all_lines)
    pieces=list(_iter_lines(noded)) if not noded.is_empty else []
    before=nx.Graph();after=nx.Graph();segments=[]
    for part in pieces:
        cs=list(part.coords)
        if len(cs)<2:continue
        for x,y in zip(cs[:-1],cs[1:]):
            a,b=_edge_key(x),_edge_key(y)
            if a==b:continue
            line=LineString([x,y]);length=GEOD.geometry_length(line)
            bad=bool(not flood_geom.is_empty and line.intersects(flood_geom))
            before.add_edge(a,b,length_m=float(length))
            if not bad:after.add_edge(a,b,length_m=float(length))
            segments.append((line,bad,float(length)))
    # Add ALL baseline nodes after so isolated nodes can still be classified.
    after.add_nodes_from(before.nodes)
    return before,after,segments


def _nearest_node(point,nodes):
    if not nodes:return None,float('inf')
    pp=(point.x,point.y)
    nearest=min(nodes,key=lambda t:(t[0]-pp[0])**2+(t[1]-pp[1])**2)
    d=GEOD.inv(pp[0],pp[1],nearest[0],nearest[1])[2]
    return nearest,float(d)


def _point_features(items, role):
    return [{'type':'Feature','properties':{'name':str(tags.get('name','Unnamed')),'role':role},'geometry':mapping(p)}
            for p,tags in items]


def estimate_impacts(osm_path,flood_geom,out_dir):
    out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
    ob=classify_osm(osm_path)
    affected_b=[(g,t) for g,t in ob['buildings'] if g.intersects(flood_geom)] if not flood_geom.is_empty else []
    affected_bridge=[(g,t) for g,t in ob['bridges'] if g.intersects(flood_geom)] if not flood_geom.is_empty else []
    before,after,segs=_road_graph(ob['roads'],flood_geom)
    total_blocked_m=sum(m for _,bad,m in segs if bad)
    # Do not infer "cut off" from lack of hospitals, absent roads or AOI-edge graph truncation.
    hospital=ob['hospitals']
    towns=[(p,t) for p,t in ob['settlements'] if t.get('place') in ('town','city')]
    anchors=hospital or towns
    nodes=list(before.nodes)
    target_nodes={_nearest_node(p,nodes)[0] for p,_ in anchors} if anchors else set()
    target_nodes.discard(None)
    cut=[];unknown=[];connected=[]
    for p,t in ob['settlements']:
        if t.get('place') in ('city','town'):continue
        n,snap_dist=_nearest_node(p,nodes)
        rec={'name':str(t.get('name','Unnamed settlement')),'place':t.get('place'),
             'lat':round(p.y,6),'lon':round(p.x,6),'snap_distance_m':round(snap_dist,1)}
        # 250m snap threshold and baseline anchor reachability prevents false isolations.
        if n is None or snap_dist>250 or not target_nodes:
            rec['reason']='missing nearest road within 250 m or no mapped hospital/town in AOI'
            unknown.append(rec);continue
        was_any=any(nx.has_path(before,n,targ) for targ in target_nodes)
        now_any=any(nx.has_path(after,n,targ) for targ in target_nodes)
        if not was_any:
            rec['reason']='not connected to mapped anchor even before event'
            unknown.append(rec)
        elif not now_any:cut.append(rec)
        else:connected.append(rec)
    impact={'buildings_exposed_count':len(affected_b),'bridges_exposed_count':len(affected_bridge),
            'blocked_road_km':round(total_blocked_m/1000,4),'settlements_likely_cut_off':len(cut),
            'settlements_still_connected':len(connected),'settlements_unknown':len(unknown),
            'anchor_type':'mapped hospital/clinic' if hospital else ('mapped town' if towns else 'none'),
            'warning':'Exposure is not verified damage. Network assumes bridges/roads intersecting hazard become unusable; missing OSM paths, elevation crossing, AOI truncation and unknown passability limit confidence.',
            'cut_off':cut,'unknown':unknown,'connected':connected}
    save_json(out_dir/'impact_metrics.json',impact)
    features=[]
    for role,items in [('exposed_building',affected_b),('exposed_bridge',affected_bridge)]:
        features.extend([{'type':'Feature','properties':{'role':role,'name':str(t.get('name',''))},'geometry':mapping(g)} for g,t in items])
    for role,recs in [('cut_off_candidate',cut),('unknown',unknown),('connected',connected)]:
        for r in recs:
            features.append({'type':'Feature','properties':{'role':role,'name':r['name']},
                             'geometry':mapping(Point(r['lon'],r['lat']))})
    for line,bad,_ in segs:
        if bad:features.append({'type':'Feature','properties':{'role':'blocked_road_candidate'},'geometry':mapping(line)})
    save_json(out_dir/'impacts.geojson',{'type':'FeatureCollection','features':features})
    return impact
