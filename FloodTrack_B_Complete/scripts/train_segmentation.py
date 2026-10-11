import argparse,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from floodtrack.train import train_model
p=argparse.ArgumentParser()
p.add_argument('--patches',default=str(root/'data/training/patches'))
p.add_argument('--model',default=str(root/'models/unet_s1.pt'))
p.add_argument('--epochs',type=int,default=10);p.add_argument('--batch',type=int,default=8)
p.add_argument('--seed',type=int,default=42)
p.add_argument('--val-sites',default='',help='Comma-delimited site IDs; REQUIRED for formal held-out Himalaya evaluation')
a=p.parse_args()
train_model(a.patches,a.model,a.epochs,a.batch,a.seed,a.val_sites.split(',') if a.val_sites else None)
