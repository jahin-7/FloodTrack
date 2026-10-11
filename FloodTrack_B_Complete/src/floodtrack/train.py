"""Optional trainable two-channel radar U-Net. Requires genuinely labeled permitted training data."""
from pathlib import Path
import json
import random
import numpy as np


def norm_vv(x):
    return np.clip((np.nan_to_num(x,nan=-30,posinf=-30,neginf=-30).astype('float32')+30)/30,0,1)


def _torch():
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise RuntimeError('PyTorch is required only for training and U-Net inference; install torch') from exc
    return torch,nn


def build_model(base=16):
    torch,nn=_torch()
    class Block(nn.Module):
        def __init__(self,a,b):
            super().__init__();self.m=nn.Sequential(nn.Conv2d(a,b,3,padding=1),nn.BatchNorm2d(b),
                       nn.ReLU(inplace=True),nn.Conv2d(b,b,3,padding=1),nn.BatchNorm2d(b),nn.ReLU(inplace=True))
        def forward(self,x):return self.m(x)
    class UNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.b1=Block(2,base);self.b2=Block(base,base*2)
            self.b3=Block(base*2,base*4)
            self.bottleneck=Block(base*4,base*8)
            self.pool=nn.MaxPool2d(2)
            self.u3=nn.ConvTranspose2d(base*8,base*4,2,2);self.d3=Block(base*8,base*4)
            self.u2=nn.ConvTranspose2d(base*4,base*2,2,2);self.d2=Block(base*4,base*2)
            self.u1=nn.ConvTranspose2d(base*2,base,2,2);self.d1=Block(base*2,base)
            self.head=nn.Conv2d(base,1,1)
        def forward(self,x):
            a=self.b1(x);b=self.b2(self.pool(a));c=self.b3(self.pool(b))
            h=self.bottleneck(self.pool(c))
            h=self.d3(torch.cat([self.u3(h),c],1))
            h=self.d2(torch.cat([self.u2(h),b],1))
            h=self.d1(torch.cat([self.u1(h),a],1))
            return self.head(h)
    return UNet()


def create_patches(pairs_root,output_root,positive_values=(1,),negative_values=(0,),patch=128):
    """User-adapted tif layout: pairs_root/SITE_ID/{pre_vv,post_vv,flood_label}.tif
    Per-dataset label values MUST be confirmed from its source; never guess an encoding.
    """
    import rasterio
    from rasterio.warp import reproject,Resampling
    inp=Path(pairs_root);out=Path(output_root);out.mkdir(parents=True,exist_ok=True)
    written=0
    for scene in sorted(inp.iterdir()):
        if not scene.is_dir():continue
        files=[scene/'pre_vv.tif',scene/'post_vv.tif',scene/'flood_label.tif']
        if not all(f.exists() for f in files):continue
        with rasterio.open(files[0]) as p, rasterio.open(files[1]) as q, rasterio.open(files[2]) as m:
            pre=p.read(1).astype('float32')
            post=np.full_like(pre,np.nan)
            label=np.full(pre.shape,255,dtype='float32')
            reproject(q.read(1),post,src_transform=q.transform,src_crs=q.crs,
                      dst_transform=p.transform,dst_crs=p.crs,resampling=Resampling.bilinear)
            reproject(m.read(1),label,src_transform=m.transform,src_crs=m.crs,
                      dst_transform=p.transform,dst_crs=p.crs,resampling=Resampling.nearest)
        y=np.full(pre.shape,255,dtype='uint8')
        y[np.isin(label,list(negative_values))]=0
        y[np.isin(label,list(positive_values))]=1
        for r in range(0,max(1,pre.shape[0]-patch+1),patch):
            for c in range(0,max(1,pre.shape[1]-patch+1),patch):
                pp=pre[r:r+patch,c:c+patch];qq=post[r:r+patch,c:c+patch];yy=y[r:r+patch,c:c+patch]
                if pp.shape!=(patch,patch) or np.count_nonzero(yy!=255)<patch*patch*.4:continue
                X=np.stack([norm_vv(pp),norm_vv(qq)])
                np.savez_compressed(out/f'{scene.name}_{r}_{c}.npz',x=X,y=yy,
                                    site=np.asarray(scene.name))
                written+=1
    if not written:
        raise RuntimeError('No patches created: check scene paths, raster CRS, label values, patch size')
    return written


def train_model(patch_dir,model_out,epochs=5,batch_size=8,seed=42,heldout_sites=None):
    torch,nn=_torch()
    from torch.utils.data import Dataset,DataLoader
    files=sorted(Path(patch_dir).glob('*.npz'))
    if len(files)<4:raise RuntimeError('Need at least 4 labeled patches; test synthetic is not a meaningful training benchmark')
    sites=sorted({str(np.load(f)['site']) for f in files})
    rng=random.Random(seed);rng.shuffle(sites)
    if len(sites)<2:raise RuntimeError('At least two independent sites are required for non-leaky validation')
    heldout=set(heldout_sites or sites[:max(1,int(len(sites)*.2))])
    if len(heldout)==len(sites):raise RuntimeError('All sites are in validation; none remain for training')
    training=[f for f in files if str(np.load(f)['site']) not in heldout]
    validation=[f for f in files if str(np.load(f)['site']) in heldout]
    if not training or not validation:raise RuntimeError('Bad geographical split; specify different heldout sites')
    class Paired(Dataset):
        def __init__(self,fs):self.fs=fs
        def __len__(self):return len(self.fs)
        def __getitem__(self,i):
            v=np.load(self.fs[i]);return torch.from_numpy(v['x']).float(),torch.from_numpy(v['y'].astype('int64'))
    train_loader=DataLoader(Paired(training),batch_size=batch_size,shuffle=True,num_workers=0)
    val_loader=DataLoader(Paired(validation),batch_size=batch_size,num_workers=0)
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    device='cuda' if torch.cuda.is_available() else 'cpu'
    model=build_model().to(device);optim=torch.optim.AdamW(model.parameters(),lr=1e-3)
    history=[];best=-1
    for ep in range(epochs):
        model.train();train_loss=[]
        for x,y in train_loader:
            x,y=x.to(device),y.to(device)
            logits=model(x)[:,0];ok=(y!=255)
            loss=nn.functional.binary_cross_entropy_with_logits(logits[ok],y[ok].float())
            optim.zero_grad();loss.backward();optim.step()
            train_loss.append(float(loss.detach().cpu()))
        model.eval();tp=fp=fn=0
        with torch.no_grad():
            for x,y in val_loader:
                pred=(torch.sigmoid(model(x.to(device))[:,0])>=.5).cpu()
                ok=(y!=255);gt=(y==1)
                tp+=int((pred&gt&ok).sum());fp+=int((pred&~gt&ok).sum());fn+=int((~pred&gt&ok).sum())
        iou=tp/max(1,tp+fp+fn)
        print(f'epoch {ep+1}/{epochs}: loss={np.mean(train_loss):.4f} site-holdout IoU={iou:.4f}')
        history.append({'epoch':ep+1,'train_bce':float(np.mean(train_loss)),'val_iou':iou})
        if iou>best:
            best=iou;Path(model_out).parent.mkdir(parents=True,exist_ok=True)
            torch.save({'model':model.state_dict(),'channels':['pre_VV_dB','post_VV_dB'],
                        'validation_sites':sorted(heldout),'training_sites':sorted(set(sites)-heldout),
                        'prototype':True,'best_val_iou':iou,'seed':seed},model_out)
    from .core import save_json
    save_json(Path(model_out).with_suffix('.training.json'),{'history':history,'site_split':{
        'validation':sorted(heldout),'training':sorted(set(sites)-heldout)},
        'warning':'Held-out scene IoU is not proof of performance on unseen Himalayan scenes unless the validation scenes are geographically independent Himalayan sites.'})
    return history


def predict_mask(checkpoint,pre,post):
    torch,nn=_torch()
    checkpoint=Path(checkpoint)
    if not checkpoint.exists():raise FileNotFoundError(checkpoint)
    # weights_only avoids arbitrary pickle object loading on modern PyTorch.
    ck=torch.load(checkpoint,map_location='cpu',weights_only=True)
    model=build_model();model.load_state_dict(ck['model']);model.eval()
    h,w=pre.shape
    H=((h+15)//16)*16;W=((w+15)//16)*16
    x=np.stack([norm_vv(pre),norm_vv(post)])
    x=np.pad(x,((0,0),(0,H-h),(0,W-w)),mode='edge')
    # Small AOI only: for full scenes implement overlap-tile stitching to avoid memory overflow.
    with torch.no_grad():prob=torch.sigmoid(model(torch.from_numpy(x).unsqueeze(0)))[0,0].numpy()
    return prob[:h,:w]
