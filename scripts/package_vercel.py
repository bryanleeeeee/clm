"""Create a lean, reproducible Vercel package without local data or secrets."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
dest=ROOT/'.deploy-vercel'
dest.mkdir(exist_ok=True)
for name in ['app.py','pyproject.toml','vercel.json','.vercelignore']:
    shutil.copy2(ROOT/name,dest/name)
for name in ['clm','public']:
    shutil.copytree(ROOT/name,dest/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','streamlit_*.py','presentation.py'))
(dest/'requirements.txt').write_text('Flask==3.1.3\npsycopg[binary]==3.3.5\n',encoding='utf-8')
print('Prepared .deploy-vercel: Python API + original Aurelia interface. Local cases, uploads and secrets excluded.')
