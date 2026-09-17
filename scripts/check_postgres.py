"""Run the opt-in database integration test using an ignored Vercel env file."""
from pathlib import Path
import json,os,subprocess,sys
root=Path(__file__).resolve().parents[1]
for line in (root/'.deploy-vercel/.env.local').read_text(encoding='utf-8-sig').splitlines():
    if line.startswith('DATABASE_URL='):
        raw=line.split('=',1)[1];os.environ['TEST_DATABASE_URL']=json.loads(raw) if raw.startswith('"') else raw
        break
else: raise SystemExit('No DATABASE_URL in local deployment environment')
raise SystemExit(subprocess.call([sys.executable,'-m','pytest','tests/test_postgres.py','-q','--tb=short','-p','no:cacheprovider'],cwd=root))
