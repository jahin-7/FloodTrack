import argparse,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from floodtrack.train import create_patches
p=argparse.ArgumentParser(description='Adapt permitted Kuro Siwo S1 raster pairs + labels to U-Net 2-channel npz')
p.add_argument('--pairs',required=True,help='Directory: site_id/pre_vv.tif,post_vv.tif,flood_label.tif')
p.add_argument('--out',default=str(root/'data/training/patches'))
p.add_argument('--positive-values',required=True,help='Comma separated, documented positive label codes from source')
p.add_argument('--negative-values',required=True,help='Comma separated, documented negative label codes from source')
p.add_argument('--patch',type=int,default=128)
a=p.parse_args()
assert a.patch%16==0,'patch multiple of 16 required'
pos=tuple(map(int,a.positive_values.split(',')))
neg=tuple(map(int,a.negative_values.split(',')))
assert not set(pos)&set(neg),'Positive and negative label values must not overlap'
n=create_patches(a.pairs,a.out,pos,neg,a.patch)
print('Patches created:',n)
