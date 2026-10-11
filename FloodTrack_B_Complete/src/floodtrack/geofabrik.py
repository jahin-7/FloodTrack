"""Free, reproducible PRE-EVENT OSM for the Nepal case study.

Downloads a dated Geofabrik country snapshot (not latest OSM), extracts the
configured AOI with osmium-tool, exports GeoJSON, and retains only the feature
tags needed for infrastructure exposure and settlement connectivity.

Requires `osmium` CLI (on Colab: apt-get install -y osmium-tool) and requests.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import requests

from .core import save_json

ARCHIVE_DATE = '2026-08-01'
ARCHIVE_URL = 'https://download.geofabrik.de/asia/nepal-260801.osm.pbf'
MD5_URL = ARCHIVE_URL + '.md5'
RELEVANT = {'building', 'highway', 'bridge', 'place', 'amenity', 'healthcare'}


def check_dates(snapshot, event):
    if str(snapshot) != ARCHIVE_DATE:
        raise ValueError(f'This archived Geofabrik file is dated {ARCHIVE_DATE}; set osm_snapshot: {ARCHIVE_DATE}, not {snapshot}.')
    if date.fromisoformat(ARCHIVE_DATE) >= date.fromisoformat(str(event)):
        raise ValueError('Archived OSM is not pre-event; refusing to run.')


def filter_osm_geojson(input_path, output_path, bbox):
    from shapely.geometry import shape, box
    fc = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if fc.get('type') != 'FeatureCollection':
        raise RuntimeError('Unexpected osmium GeoJSON output')
    region = box(*map(float, bbox))
    result = []
    for f in fc.get('features', []):
        props = f.get('properties') or {}
        if not any(k in props for k in RELEVANT):
            continue
        if 'amenity' in props and props.get('amenity') not in ('hospital', 'clinic') and not any(k in props for k in ('building', 'highway', 'bridge', 'place', 'healthcare')):
            continue
        if 'healthcare' in props and props.get('healthcare') not in ('hospital', 'clinic') and not any(k in props for k in ('building', 'highway', 'bridge', 'place', 'amenity')):
            continue
        geom = f.get('geometry')
        if not geom:
            continue
        try:
            if not shape(geom).intersects(region):
                continue
        except Exception:
            continue
        result.append({'type': 'Feature', 'geometry': geom, 'properties': props})
    if not result:
        raise RuntimeError('No relevant OSM features in AOI; verify the bbox and source extract.')
    save_json(output_path, {'type': 'FeatureCollection', 'features': result})
    return len(result)


def download_file(url, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 100_000_000:
        print('Using cached Geofabrik snapshot:', path)
        return
    part = path.with_suffix(path.suffix + '.part')
    for attempt in range(3):
        start = part.stat().st_size if part.exists() else 0
        headers = {'Range': f'bytes={start}-'} if start else {}
        try:
            with requests.get(url, headers=headers, stream=True, timeout=(30, 120), allow_redirects=True) as resp:
                resp.raise_for_status()
                if start and resp.status_code != 206:
                    start = 0  # server ignored Range: restart rather than corrupt file
                mode = 'ab' if start else 'wb'
                with part.open(mode) as out:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            out.write(chunk)
            if part.stat().st_size <= 100_000_000:
                raise RuntimeError('Archive unexpectedly small or incomplete')
            part.replace(path)
            return
        except (requests.RequestException, RuntimeError) as e:
            print(f'Download attempt {attempt + 1}/3 failed: {type(e).__name__}: {e}')
            if attempt == 2:
                raise


def verify_md5(path):
    # Geofabrik publishes the checksum alongside the exact archived file.
    resp = requests.get(MD5_URL, timeout=25)
    resp.raise_for_status()
    match = re.search(r'\b([a-fA-F0-9]{32})\b', resp.text)
    if not match:
        raise RuntimeError('Cannot parse Geofabrik MD5 checksum; refusing unverifiable input.')
    h = hashlib.md5()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    if h.hexdigest().lower() != match.group(1).lower():
        raise RuntimeError('Geofabrik archive checksum mismatch; delete cache and retry.')
    return h.hexdigest()


def acquire(cfg, dest, cache_dir=None):
    check_dates(cfg['osm_snapshot'], cfg['case_event_date'])
    if len(cfg['bbox']) != 4:
        raise ValueError('bbox must be [west, south, east, north]')
    if not (cfg['bbox'][0] < cfg['bbox'][2] and cfg['bbox'][1] < cfg['bbox'][3]):
        raise ValueError('Invalid bbox ordering')
    cache = Path(cache_dir or os.environ.get('FLOODTRACK_OSM_CACHE', '/content/geofabrik_cache'))
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / 'nepal-260801.osm.pbf'
    clipped = Path(dest).parent / (cfg['name'] + '_historical_clip.osm.pbf')
    exported = cache / (cfg['name'] + '_export.geojson')
    download_file(ARCHIVE_URL, archive)
    checksum = verify_md5(archive)
    bbox = ','.join(map(str, cfg['bbox']))
    print('Extracting AOI from verified pre-event Nepal OSM archive...')
    subprocess.run(['osmium', 'extract', '--bbox', bbox, '--strategy', 'complete_ways',
                    '--output', str(clipped), '--overwrite', str(archive)], check=True)
    print('Converting clipped OSM to GeoJSON...')
    subprocess.run(['osmium', 'export', str(clipped), '--output', str(exported), '--overwrite'], check=True)
    n = filter_osm_geojson(exported, dest, cfg['bbox'])
    meta = {'source': 'Geofabrik dated Nepal OpenStreetMap extract',
            'source_url': ARCHIVE_URL, 'snapshot': ARCHIVE_DATE,
            'source_md5': checksum, 'features': n, 'post_event_osm_used': False,
            'license': 'ODbL 1.0', 'attribution': '© OpenStreetMap contributors',
            'aoi_bbox': cfg['bbox'], 'extraction': 'osmium extract complete_ways + osmium export'}
    return meta


