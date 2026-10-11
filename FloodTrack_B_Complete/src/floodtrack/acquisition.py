"""Copernicus Data Space satellite acquisition + pre-event ohsome historical OSM.

No Google Earth Engine and no EMS/UNOSAT data in inference. Sentinel Hub's
Processing API delivers calibrated/orthorectified *derived* GeoTIFFs from
Sentinel-1 GRD; this is NOT a raw SAFE processing implementation.
"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from math import cos, radians, ceil
import os
import requests
import numpy as np
import rasterio
from .core import save_json

STAC_SEARCH = 'https://stac.dataspace.copernicus.eu/v1/search'
TOKEN_URL = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
PROCESS_URL = 'https://sh.dataspace.copernicus.eu/process/v1'
TIMEOUT = 180
NODATA = -9999.0


def _utc(ts):
    return datetime.fromisoformat(str(ts).replace('Z', '+00:00')).astimezone(timezone.utc)


def _stac_items(collection, bbox, start, end, session=None, limit_pages=8):
    """Public CDSE STAC, paginated; metadata only (no secret needed)."""
    http = session or requests.Session()
    body = {'collections': [collection], 'bbox': list(map(float, bbox)),
            'datetime': f'{start}T00:00:00Z/{end}T23:59:59Z', 'limit': 100}
    url, method = STAC_SEARCH, 'POST'
    items = []
    for _ in range(limit_pages):
        if method == 'POST':
            r = http.post(url, json=body, timeout=TIMEOUT)
        elif method == 'GET':
            r = http.get(url, timeout=TIMEOUT)
        else:
            raise RuntimeError('Unsupported STAC pagination method')
        r.raise_for_status()
        page = r.json()
        items.extend(page.get('features', []))
        next_link = next((x for x in page.get('links', []) if x.get('rel') == 'next'), None)
        if not next_link:
            return items
        href = next_link.get('href', '')
        if not href.startswith('https://stac.dataspace.copernicus.eu/'):
            raise RuntimeError('Unexpected STAC pagination host')
        url, method = href, next_link.get('method', 'GET').upper()
        if method == 'POST':
            body = next_link.get('body', body)
    raise RuntimeError('STAC pagination limit reached; narrow bbox/date window')


def _s1_candidates(items):
    scenes = []
    for f in items:
        p = f.get('properties') or {}
        rel = p.get('sat:relative_orbit')
        orbit = str(p.get('sat:orbit_state') or '').upper()
        polar = p.get('sar:polarizations') or p.get('s1:polarization') or []
        if isinstance(polar, str):
            polar = [polar]
        mode = str(p.get('sar:instrument_mode') or p.get('s1:instrument_mode') or 'IW').upper()
        if rel is None or orbit not in ('ASCENDING', 'DESCENDING') or mode != 'IW' or 'VV' not in polar:
            continue
        ts = p.get('datetime') or p.get('start_datetime')
        if not ts:
            continue
        scenes.append({'id': str(f.get('id')), 'utc': _utc(ts).isoformat(),
                       'time': _utc(ts), 'relative_orbit': int(rel),
                       'orbit_pass': orbit, 'instrument_mode': mode,
                       'polarizations': polar})
    return scenes


def select_same_orbit_pair(items, event_date):
    """Hard requirement: same relative orbit + pass, opposite sides of event."""
    evt = datetime.combine(date.fromisoformat(str(event_date)), datetime.min.time(), timezone.utc)
    scenes = _s1_candidates(items)
    pre = [s for s in scenes if s['time'] < evt]
    post = [s for s in scenes if s['time'] >= evt]
    pairs = [(a, b) for a in pre for b in post if
             a['relative_orbit'] == b['relative_orbit'] and a['orbit_pass'] == b['orbit_pass']]
    if not pairs:
        raise RuntimeError('No same-relative-orbit/same-pass Sentinel-1 VV IW pair. Expand date windows or change AOI; do not compare different tracks.')
    a, b = min(pairs, key=lambda ab: (
        (ab[1]['time']-evt).total_seconds()/86400 +
        (evt-ab[0]['time']).total_seconds()/86400 * 0.1 +
        abs((ab[1]['time']-ab[0]['time']).total_seconds()/86400-12) * 0.15))
    return a, b


def _token(session=None, client_id=None, client_secret=None):
    cid = client_id or os.getenv('CDSE_CLIENT_ID')
    secret = client_secret or os.getenv('CDSE_CLIENT_SECRET')
    if not cid or not secret:
        raise RuntimeError('Missing CDSE_CLIENT_ID and CDSE_CLIENT_SECRET. Create a Sentinel Hub OAuth client in the Copernicus Data Space dashboard and set environment variables (never store secrets in notebooks).')
    http = session or requests.Session()
    r = http.post(TOKEN_URL, data={'grant_type': 'client_credentials',
                     'client_id': cid, 'client_secret': secret}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()['access_token']


def _dims(bbox, scale_m):
    xmin,ymin,xmax,ymax = map(float,bbox)
    midlat=(ymin+ymax)/2
    width=max(1,ceil((xmax-xmin)*111320*cos(radians(midlat))/float(scale_m)))
    height=max(1,ceil((ymax-ymin)*111320/float(scale_m)))
    if width > 2400 or height > 2400 or width*height > 4_000_000:
        raise ValueError(f'AOI {width}x{height} pixels exceeds synchronous request safety limit. Tile the AOI or raise scale_m.')
    return width,height


def _request(bbox, width, height, source, evalscript):
    return {'input': {'bounds': {'bbox': list(map(float,bbox)),
               'properties': {'crs': 'http://www.opengis.net/def/crs/OGC/1.3/CRS84'}},
               'data': [source]},
            'output': {'width': width, 'height': height,
               'responses': [{'identifier': 'default', 'format': {'type': 'image/tiff'}}]},
            'evalscript': evalscript}


S1_EVAL = '''//VERSION=3
function setup() { return {input: ["VV", "dataMask"], output: {bands: 1, sampleType: "FLOAT32"}}; }
function evaluatePixel(s) {
  if (!s.dataMask || !(s.VV > 0)) return [-9999];
  return [10 * Math.log(s.VV) / Math.LN10];
}
'''
S2_EVAL = '''//VERSION=3
function setup() { return {input: ["B03", "B08", "SCL", "dataMask"], output: {bands: 1, sampleType: "FLOAT32"}}; }
function evaluatePixel(s) {
  if (!s.dataMask || [0,1,3,8,9,10,11].indexOf(s.SCL) >= 0) return [-9999];
  var sum = s.B03 + s.B08;
  return sum > 0 ? [(s.B03-s.B08)/sum] : [-9999];
}
'''
DEM_EVAL = '''//VERSION=3
function setup() { return {input: ["DEM", "dataMask"], output: {bands: 1, sampleType: "FLOAT32"}}; }
function evaluatePixel(s) { return s.dataMask ? [s.DEM] : [-9999]; }
'''


def _process(http, token, payload, destination):
    dest=Path(destination); dest.parent.mkdir(parents=True,exist_ok=True)
    response=http.post(PROCESS_URL, json=payload, headers={'Authorization': f'Bearer {token}',
                  'Accept': 'image/tiff'}, timeout=TIMEOUT)
    if response.status_code != 200:
        raise RuntimeError(f'CDSE Processing API HTTP {response.status_code}: {response.text[:350]}')
    if response.content[:4] not in (b'II*\x00', b'MM\x00*'):
        raise RuntimeError('CDSE response was not a TIFF; check service permissions/quota')
    dest.write_bytes(response.content)
    with rasterio.open(dest) as src:
        if src.count != 1 or not src.crs:
            raise RuntimeError('CDSE raster lacks expected single-band georeferencing')
    return dest


def _source(collection, start, end, orbit=None, polarization='DV'):
    filt={'timeRange': {'from': start, 'to': end}}
    if orbit:
        filt.update({'orbitDirection': orbit, 'acquisitionMode': 'IW', 'polarization': polarization})
    src={'type': collection, 'dataFilter': filt}
    if orbit:
        src['processing']={'orthorectify': True, 'backCoeff': 'GAMMA0_TERRAIN'}
    elif collection == 'dem':
        src['dataFilter']={'demInstance': 'COPERNICUS_30'}
    return src


def _window(scene, minutes=4):
    dt=scene['time']; return ((dt-timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                               (dt+timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M:%SZ'))


def _combine(pre_path, post_path, dest):
    with rasterio.open(pre_path) as p, rasterio.open(post_path) as q:
        if (p.crs != q.crs or p.transform != q.transform or
                p.width != q.width or p.height != q.height):
            raise RuntimeError('Satellite pair not on exactly the same grid')
        profile=p.profile.copy()
        profile.update(count=2, dtype='float32', nodata=NODATA, compress='deflate')
        with rasterio.open(dest,'w',**profile) as out:
            out.write(p.read(1).astype('float32'),1)
            out.write(q.read(1).astype('float32'),2)
    return dest


def _optional_s2(http, token, cfg, out, bbox, width, height, evt, meta):
    days=int(cfg.get('optical_search_days',35))
    items=_stac_items('sentinel-2-l2a', bbox, (evt-timedelta(days=days)).isoformat(),
                      (evt+timedelta(days=days)).isoformat(), session=http)
    pre=[];post=[]
    for f in items:
        p=f.get('properties') or {}
        ts=p.get('datetime')
        if not ts: continue
        t=_utc(ts)
        cloud=float(p.get('eo:cloud_cover') if p.get('eo:cloud_cover') is not None else 100)
        (pre if t < datetime.combine(evt,datetime.min.time(),timezone.utc) else post).append((t,cloud,f['id']))
    if not pre or not post:
        meta['optical']='no pre/post Sentinel-2 L2A scenes in configured window';return
    # prioritize low cloud cover and closeness to event
    ed=datetime.combine(evt,datetime.min.time(),timezone.utc)
    pick=lambda seq: min(seq,key=lambda x:(x[1]*.5+abs((x[0]-ed).total_seconds())/86400))
    a,b=pick(pre),pick(post)
    paths=[]
    for idx,scene in enumerate((a,b)):
        start=(scene[0]-timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
        end=(scene[0]+timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
        path=out/f'_s2_{idx}.tif'
        _process(http,token,_request(bbox,width,height,
              _source('sentinel-2-l2a',start,end),S2_EVAL),path)
        paths.append(path)
    _combine(*paths,out/'s2_ndwi.tif')
    for p in paths:p.unlink(missing_ok=True)
    meta['optical']={'pre_id':a[2],'post_id':b[2],'pre_utc':a[0].isoformat(),
                     'post_utc':b[0].isoformat(),'pre_cloud_pct':a[1],
                     'post_cloud_pct':b[1],'mask':'SCL cloud/shadow/snow mask'}


def acquire_satellite(cfg, output_dir, session=None):
    """Acquire CDSE S1 pre/post VV dB; optional S2 NDWI and Copernicus DEM.

    Does not pretend to have run without valid OAuth credentials and API access.
    """
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    bbox=cfg['bbox'];evt=date.fromisoformat(str(cfg['case_event_date']))
    width,height=_dims(bbox,cfg.get('scale_m',30))
    http=session or requests.Session()
    scenes=_stac_items('sentinel-1-grd',bbox,
             (evt-timedelta(days=int(cfg.get('lookback_days',30)))).isoformat(),
             (evt+timedelta(days=int(cfg.get('lookforward_days',25)))).isoformat(),session=http)
    a,b=select_same_orbit_pair(scenes,evt)
    token=_token(http)
    paths=[]
    for idx,scene in enumerate((a,b)):
        start,end=_window(scene)
        src=_source('sentinel-1-grd',start,end,scene['orbit_pass'],
                    'DV' if 'VH' in scene['polarizations'] else 'SV')
        path=out/f'_s1_{idx}.tif'
        _process(http,token,_request(bbox,width,height,src,S1_EVAL),path)
        paths.append(path)
    _combine(*paths,out/'s1_pair.tif')
    for p in paths:p.unlink(missing_ok=True)
    with rasterio.open(out/'s1_pair.tif') as src:
        pair=src.read(); valid=np.isfinite(pair).all(axis=0)&(pair[0]>-70)&(pair[1]>-70)
        if not valid.any():
            raise RuntimeError('S1 returned no valid overlapping VV data; inspect STAC acquisition windows')
    meta={'source':'Copernicus Data Space STAC + Sentinel Hub Processing API',
          'input':'Sentinel-1 GRD (VV), not raw SAFE',
          'pre_id':a['id'],'post_id':b['id'],
          'pre_utc':a['utc'],'post_utc':b['utc'],
          'relative_orbit':a['relative_orbit'],'orbit_pass':a['orbit_pass'],
          'same_orbit_verified':True,
          'acquisition_gap_days':round((b['time']-a['time']).total_seconds()/86400,4),
          's1_processing':'orthorectified GAMMA0_TERRAIN linear power -> 10log10 dB; -9999 invalid',
          's1_valid_overlap_fraction':round(float(valid.mean()),4),
          'resolution_m_approx':cfg.get('scale_m',30),'shape':[height,width],
          'optical':'not_requested','dem':'not_requested',
          'api':'https://sh.dataspace.copernicus.eu/process/v1'}
    if cfg.get('use_optical',True):
        try:
            _optional_s2(http,token,cfg,out,bbox,width,height,evt,meta)
        except Exception as exc:
            meta['optical']=f'Unavailable; radar-only: {type(exc).__name__}: {str(exc)[:180]}'
    if cfg.get('use_dem',True):
        try:
            _process(http,token,_request(bbox,width,height,
               _source('dem','',''),DEM_EVAL),out/'copernicus_dem.tif')
            meta['dem']='Copernicus DEM GLO-30 via CDSE Sentinel Hub'
        except Exception as exc:
            meta['dem']=f'Unavailable: {type(exc).__name__}: {str(exc)[:180]}'
    save_json(out/'satellite_provenance.json',meta)
    return meta


def _historical_snapshot_from_full_history(data, snapshot):
    """Select OSM versions active at the pre-event instant, never later edits.

    ohsome v1 full-history features carry @validFrom and @validTo. The
    extraction window is deliberately short but must include the instant.
    Missing validity metadata is an error, not a reason to use present OSM.
    """
    if data.get('type') != 'FeatureCollection' or not isinstance(data.get('features'), list):
        raise RuntimeError('ohsome full-history returned an unexpected payload')
    instant = _utc(str(snapshot) + 'T00:00:00Z')
    selected = {}
    for feature in data['features']:
        props = feature.get('properties') or {}
        start, end = props.get('@validFrom'), props.get('@validTo')
        if not start or not end:
            raise RuntimeError('ohsome full-history missing @validFrom/@validTo; refusing unsafe OSM snapshot')
        if not (_utc(start) <= instant < _utc(end)):
            continue
        if not feature.get('geometry'):
            continue
        # Preserve the complete way geometry and tags for road graph analysis.
        osm_id = props.get('@osmId') or feature.get('id')
        if osm_id is None:
            raise RuntimeError('ohsome full-history missing OSM ID; cannot deduplicate')
        if osm_id in selected:
            raise RuntimeError('Duplicate active versions of an OSM element in history result')
        selected[osm_id] = feature
    if not selected:
        raise RuntimeError('No active OSM features found at snapshot; check API response and AOI')
    return {'type': 'FeatureCollection', 'features': list(selected.values())}


def download_osm_snapshot(cfg, dest, session=None):
    """Historical OSM, with safe fallback for the known ohsome v1 geometry 403.

    Never silently substitute current OSM/Overpass, which can contain
    post-disaster edits and invalidate hackathon results.
    """
    snap = str(cfg['osm_snapshot'])
    if date.fromisoformat(snap) >= date.fromisoformat(str(cfg['case_event_date'])):
        raise ValueError('Post-event OSM forbidden')
    filt = ('(building=* or highway=* or bridge=* or place=* or amenity=hospital '
            'or amenity=clinic or healthcare=hospital or healthcare=clinic)')
    base = {'bboxes': ','.join(map(str, cfg['bbox'])), 'filter': filt,
            'properties': 'tags,metadata', 'clipGeometry': 'false'}
    http = session or requests.Session()
    standard_url = 'https://api.ohsome.org/v1/elements/geometry'
    primary = http.post(standard_url, data={**base, 'time': snap}, timeout=240)
    if primary.status_code == 200:
        js = primary.json()
        if js.get('type') != 'FeatureCollection' or not isinstance(js.get('features'), list):
            raise RuntimeError('Unexpected historical ohsome snapshot response')
        source, endpoint = 'ohsome v1 snapshot', standard_url
    elif primary.status_code in (403, 404, 429, 500, 502, 503, 504):
        # The v1 snapshot geometry endpoint has a known 403 since July 2026.
        # Full-history geometry was reported to work. Request the versions
        # straddling snapshot and filter validity timestamps explicitly.
        history_url = 'https://api.ohsome.org/v1/elementsFullHistory/geometry'
        start = (date.fromisoformat(snap) - timedelta(days=1)).isoformat()
        end = (date.fromisoformat(snap) + timedelta(days=1)).isoformat()
        history = http.post(history_url,
                            data={**base, 'time': f'{start},{end}'}, timeout=240)
        if history.status_code != 200:
            raise RuntimeError(
                f'Historical OSM unavailable: snapshot endpoint HTTP {primary.status_code}; '
                f'full-history endpoint HTTP {history.status_code}. '
                'Do NOT substitute present-day Overpass. Use a verified pre-event '
                'OSM snapshot GeoJSON and staged mode, or retry later.')
        js = _historical_snapshot_from_full_history(history.json(), snap)
        source, endpoint = 'ohsome v1 full-history reconstructed pre-event snapshot', history_url
    else:
        raise RuntimeError(f'ohsome historical OSM HTTP {primary.status_code}: '
                           f'{primary.text[:200]}')
    if not js['features']:
        raise RuntimeError('Historical OSM returned no features; check AOI and snapshot')
    path = Path(dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_json(path, js)
    return {'source': source, 'snapshot': snap, 'features': len(js['features']),
            'filter': filt, 'endpoint': endpoint,
            'post_event_osm_used': False}
