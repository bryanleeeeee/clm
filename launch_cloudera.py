"""Cloudera AI Application launch file for the native Streamlit interface."""
import os
import subprocess
import sys
from pathlib import Path
if __name__ == '__main__':
    root=Path(__file__).resolve().parent
    port=os.environ.get('CDSW_APP_PORT','8080')
    raise SystemExit(subprocess.call([sys.executable,'-m','streamlit','run',str(root/'streamlit_app.py'),'--server.address=0.0.0.0',f'--server.port={port}','--server.headless=true'],cwd=root))
