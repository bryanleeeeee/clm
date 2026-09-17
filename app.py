"""Portable WSGI entry point: python app.py (no Node.js required)."""
import os
from clm.web import create_app
app = create_app()
if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('CDSW_APP_PORT', os.environ.get('PORT', '4173')))
    host = os.environ.get('HOST', '0.0.0.0' if 'CDSW_APP_PORT' in os.environ else '127.0.0.1')
    print(f'Aurelia Flask running at http://{host}:{port} — SYNTHETIC DATA ONLY', flush=True)
    serve(app, host=host, port=port, threads=8, max_request_body_size=15*1024*1024)
