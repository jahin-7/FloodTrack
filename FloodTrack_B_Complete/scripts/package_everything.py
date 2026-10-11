"""Zip entire reproducible project, not outputs only. Exclude credentials and secrets."""
import argparse,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--out',default=str(root.parent/'FloodTrack_B_Full_Project.zip'))
p.add_argument('--omit-large-data',action='store_true',help='Optional shareable source-only ZIP; default includes raw and results')
a=p.parse_args()
zip_path=Path(a.out).resolve();zip_path.parent.mkdir(parents=True,exist_ok=True)
excluded={'.git','.pytest_cache','__pycache__','.ipynb_checkpoints','.venv','.env','.earthengine'}
def safe(f):
    if any(x in excluded for x in f.parts):return False
    lower=f.name.lower()
    if any(s in lower for s in ('credential','service_account','secret','token','.pem','.key')):return False
    if a.omit_large_data and ('data' in f.parts or 'outputs' in f.parts):
        return f.name=='.gitkeep'
    return True
entries=[]
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
    for f in root.rglob('*'):
        if not f.is_file() or f.resolve()==zip_path or not safe(f.relative_to(root)):continue
        z.write(f,arcname=str(Path(root.name)/f.relative_to(root)));entries.append(str(f.relative_to(root)))
print(f'Archive: {zip_path} | files: {len(entries)} | bytes: {zip_path.stat().st_size:,}')
