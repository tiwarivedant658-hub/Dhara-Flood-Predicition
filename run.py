"""
run.py
------
Single entry point for the whole project. From the project root, run:

    python run.py

This starts the Flask server (backend/app.py) which both serves the API
AND the frontend (index.html / css / js) on the same port, so you only
ever need to open ONE url: http://localhost:5000

See README.md for full setup instructions.
"""

from backend.app import app
from backend import config

if __name__ == "__main__":
    print("=" * 60)
    print(" Flash Flood Prediction System - SIH PS 192")
    print(f" Starting server on http://localhost:{config.PORT}")
    print(" Press CTRL+C to stop")
    print("=" * 60)
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
