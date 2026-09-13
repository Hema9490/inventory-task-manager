"""
Local dev entry point. In production (Render), gunicorn imports
`app:create_app()` directly via the Procfile — this file is only for
`python run.py` during local development.
"""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
