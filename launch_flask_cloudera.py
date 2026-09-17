"""Select this file as the Cloudera AI Application launch script."""
import os
from waitress import serve
from clm.web import create_app
if __name__ == '__main__':
    port=int(os.environ.get('CDSW_APP_PORT', '8080'))
    print(f'Starting Aurelia on Cloudera application port {port}; synthetic data only.',flush=True)
    serve(create_app(), host='0.0.0.0', port=port, threads=8, max_request_body_size=15*1024*1024)
