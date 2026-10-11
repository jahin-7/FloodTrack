"""Tests for strict pre-event OSM historical fallback, no network needed."""
import sys
from pathlib import Path
import json
from datetime import date
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from floodtrack.acquisition import download_osm_snapshot, _historical_snapshot_from_full_history

CFG={'bbox':[85.119,28.15,85.157,28.182], 'osm_snapshot':'2026-07-27', 'case_event_date':'2026-08-26'}

def feat(osm_id, start, end):
    return {'type':'Feature','geometry':{'type':'LineString','coordinates':[[85.12,28.15],[85.13,28.16]]},
            'properties':{'@osmId':osm_id, '@validFrom':start, '@validTo':end, 'highway':'primary'}}

class Resp:
    def __init__(self,status,body):self.status_code=status;self.body=body;self.text=str(body)
    def json(self):return self.body
class Session:
    def __init__(self):self.calls=[]
    def post(self,url,**kwargs):
        self.calls.append((url,kwargs))
        if 'FullHistory' not in url:return Resp(403,{})
        return Resp(200,{'type':'FeatureCollection','features':[
            feat('way/1','2026-07-26T00:00:00Z','2026-07-27T10:00:00Z'),
            feat('way/1','2026-07-27T10:00:00Z','2026-07-28T00:00:00Z'),
            feat('way/2','2026-07-26T00:00:00Z','2026-07-28T00:00:00Z')]})

def test_403_fallback_filters_later_versions(tmp_path):
    session=Session();dest=tmp_path/'historic.geojson'
    meta=download_osm_snapshot(CFG,dest,session)
    assert meta['post_event_osm_used'] is False
    assert 'full-history' in meta['source']
    assert len(session.calls)==2
    assert session.calls[1][1]['data']['time']=='2026-07-26,2026-07-28'
    js=json.loads(dest.read_text())
    assert len(js['features'])==2
    assert js['features'][0]['properties']['@validTo']=='2026-07-27T10:00:00Z'

def test_missing_validity_rejected():
    f=feat('way/1','2026-07-26T00:00:00Z','2026-07-28T00:00:00Z')
    del f['properties']['@validTo']
    with pytest.raises(RuntimeError,match='missing @validFrom'):
        _historical_snapshot_from_full_history({'type':'FeatureCollection','features':[f]},'2026-07-27')

def test_no_post_event_osm(tmp_path):
    bad={**CFG,'osm_snapshot':'2026-08-27'}
    with pytest.raises(ValueError,match='Post-event'):
        download_osm_snapshot(bad,tmp_path/'osm.geojson',Session())

def test_no_current_osm_fallback(tmp_path):
    class Fails(Session):
        def post(self,url,**kwargs):
            return Resp(403,{})
    with pytest.raises(RuntimeError,match='Do NOT substitute'):
        download_osm_snapshot(CFG,tmp_path/'osm.geojson',Fails())
