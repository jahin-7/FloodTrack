"""Only for smoke-testing I/O, not evaluation or claimed environmental findings."""
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from .core import save_json

def create_synthetic(cfg,raw,osm_path):
    raw=Path(raw);raw.mkdir(parents=True,exist_ok=True)
    N=128
    y,x=np.mgrid[0:N,0:N]
    stream=(np.abs(x-(60+11*np.sin(y/17)))<10)
    rng=np.random.default_rng(42)
    pre=(-9+rng.normal(0,1.4,(N,N))).astype('float32')
    post=pre.copy();post[stream]-=8.2
    transform=from_bounds(*cfg['bbox'],width=N,height=N)
    # from_bounds expects west,south,east,north, as in cfg bbox.
    profile={'driver':'GTiff','height':N,'width':N,'count':2,'dtype':'float32',
             'crs':'EPSG:4326','transform':transform,'compress':'deflate','nodata':-9999}
    with rasterio.open(raw/'s1_pair.tif','w',**profile) as ds:
        ds.write(pre,1);ds.write(post,2)
    op=np.full((N,N),-.3,dtype='float32');oa=op.copy();oa[stream]=.65
    with rasterio.open(raw/'s2_ndwi.tif','w',**profile) as ds:
        ds.write(op,1);ds.write(oa,2)
    dem=np.full((N,N),800,dtype='float32')
    with rasterio.open(raw/'copernicus_dem.tif','w',**{**profile,'count':1}) as ds:ds.write(dem,1)
    w,s,e,n=cfg['bbox'];cx=(w+e)/2;cy=(s+n)/2
    def feature(geometry,**tags):return {'type':'Feature','geometry':geometry,'properties':tags}
    def point(x,y):return {'type':'Point','coordinates':[x,y]}
    def line(cs):return {'type':'LineString','coordinates':cs}
    roads=[]
    roads.append(feature(line([[w+.002,cy],[e-.002,cy]]),highway='residential',name='Main road'))
    roads.append(feature(line([[cx-.009,s+.004],[cx-.009,n-.004]]),highway='residential',name='Cross road'))
    roads.append(feature(line([[cx+.009,s+.004],[cx+.009,n-.004]]),highway='residential',name='Access road'))
    roads.append(feature(line([[cx-.005,cy],[cx+.005,cy]]),highway='secondary',bridge='yes',name='Demo bridge'))
    settlements=[feature(point(cx-.015,cy),place='village',name='Village A'),
                 feature(point(cx+.015,cy),place='village',name='Village B'),
                 feature(point(w+.003,cy),place='town',name='Town')]
    hospitals=[feature(point(w+.003,cy),amenity='hospital',name='Demo clinic')]
    bld=[]
    for lon,lat in [(cx,cy),(cx+.004,cy+.001),(cx-.003,cy-.003)]:
        d=.0005
        bld.append(feature({'type':'Polygon','coordinates':[[[lon-d,lat-d],[lon+d,lat-d],
            [lon+d,lat+d],[lon-d,lat+d],[lon-d,lat-d]]]},building='yes'))
    save_json(osm_path,{'type':'FeatureCollection','features':roads+settlements+hospitals+bld,
                       'metadata':{'synthetic':True,'snapshot':cfg['osm_snapshot']}})
