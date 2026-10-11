"""Offline tests for Copernicus Data Space integration. No live account needed."""
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from floodtrack import acquisition as cdse


def scene(id,ts,orbit,pass_='DESCENDING',polar=('VV','VH')):
    return {'id':id,'properties':{'datetime':ts,'sat:relative_orbit':orbit,
       'sat:orbit_state':pass_.lower(),'sar:polarizations':list(polar),
       'sar:instrument_mode':'IW'}}


def test_same_orbit_pair_ignores_mismatched_track():
    records=[scene('old_wrong','2026-08-25T12:00:00Z',3),
             scene('pre','2026-08-20T12:00:00Z',44),
             scene('post','2026-09-01T12:00:00Z',44)]
    a,b=cdse.select_same_orbit_pair(records,'2026-08-26')
    assert (a['id'],b['id'])==('pre','post')
    with pytest.raises(RuntimeError,match='same-relative-orbit'):
        cdse.select_same_orbit_pair(records[:2],'2026-08-26')


def test_request_payload_has_terrain_correction_and_db():
    src=cdse._source('sentinel-1-grd','2026-08-20T00:00:00Z',
       '2026-08-20T23:59:59Z','DESCENDING')
    req=cdse._request([85,28,85.05,28.05],200,200,src,cdse.S1_EVAL)
    assert req['input']['data'][0]['processing']['backCoeff']=='GAMMA0_TERRAIN'
    assert req['input']['data'][0]['processing']['orthorectify'] is True
    assert 'Math.log' in req['evalscript']
    assert req['output']['responses'][0]['format']['type']=='image/tiff'


def test_missing_auth_does_not_fall_back(monkeypatch):
    monkeypatch.delenv('CDSE_CLIENT_ID',raising=False)
    monkeypatch.delenv('CDSE_CLIENT_SECRET',raising=False)
    with pytest.raises(RuntimeError,match='CDSE_CLIENT_ID'):
        cdse._token()


def test_acquire_rasters_and_provenance_offline(tmp_path,monkeypatch):
    records=[scene('pre','2026-08-20T12:00:00Z',44),
             scene('post','2026-09-01T12:00:00Z',44)]
    monkeypatch.setattr(cdse,'_stac_items',lambda *args,**kwargs:records)
    monkeypatch.setattr(cdse,'_token',lambda *args,**kwargs:'mock-token')
    calls=[]
    def fake_process(http,token,payload,dest):
        calls.append(payload)
        dest=Path(dest)
        bounds=payload['input']['bounds']['bbox']
        h,w=payload['output']['height'],payload['output']['width']
        profile=dict(driver='GTiff',height=h,width=w,count=1,dtype='float32',
             crs='EPSG:4326',transform=from_bounds(*bounds,w,h),nodata=-9999)
        with rasterio.open(dest,'w',**profile) as ds:
            ds.write(np.full((h,w),-12 if len(calls)==1 else -18,dtype='float32'),1)
        return dest
    monkeypatch.setattr(cdse,'_process',fake_process)
    cfg={'bbox':[85.119,28.15,85.124,28.155], 'case_event_date':'2026-08-26',
         'scale_m':30,'use_optical':False,'use_dem':False}
    meta=cdse.acquire_satellite(cfg,tmp_path)
    assert len(calls)==2
    assert meta['same_orbit_verified'] and meta['relative_orbit']==44
    assert meta['source'].startswith('Copernicus Data Space')
    with rasterio.open(tmp_path/'s1_pair.tif') as ds:
        assert ds.count==2 and ds.crs.to_epsg()==4326
        assert ds.read(1).mean()==-12 and ds.read(2).mean()==-18
    assert json.loads((tmp_path/'satellite_provenance.json').read_text())['post_id']=='post'
    assert not list(tmp_path.glob('_s1_*'))


def test_stac_pagination_and_host_restriction():
    class Response:
        def __init__(self,data):self.data=data
        def raise_for_status(self):pass
        def json(self):return self.data
    class Session:
        def __init__(self):self.n=0
        def post(self,*args,**kwargs):
            self.n+=1
            return Response({'features':[{'id':'one'}], 'links':[{'rel':'next','method':'GET',
                 'href':'https://stac.dataspace.copernicus.eu/v1/search?page=2'}]})
        def get(self,*args,**kwargs):
            return Response({'features':[{'id':'two'}], 'links':[]})
    items=cdse._stac_items('sentinel-1-grd',[85,28,85.1,28.1],'2026-08-01','2026-09-01',Session())
    assert [i['id'] for i in items]==['one','two']
