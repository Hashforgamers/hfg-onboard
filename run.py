# run.py

import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    debug = os.getenv("DEBUG_MODE", "false").lower() == "true"
    app.run(host='0.0.0.0', port=5052, debug=debug)
