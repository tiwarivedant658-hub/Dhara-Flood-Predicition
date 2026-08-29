"""
config.py
---------
Loads configuration from environment variables (via a .env file at the
project root) and exposes them as simple constants the rest of the backend
imports from. Keeping this in one place means nobody has to hunt through
app.py to find where a setting comes from.

No secret keys are hard-coded here. If a value is missing from .env we fall
back to a safe default so the app still runs out of the box.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Project root = one level above /backend
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- Server ---
FLASK_ENV = os.getenv("FLASK_ENV", "development")
PORT = int(os.getenv("PORT", 5000))
DEBUG = FLASK_ENV != "production"

# --- Weather / soil moisture data source ---
# Open-Meteo is free and needs NO API key for the endpoints this project
# uses (forecast + historical weather). It is the default data source so the
# project works immediately after `pip install -r requirements.txt`.
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Optional: if the team gets an OpenWeatherMap key, it can be used as a
# secondary/fallback data source later. Leave blank to skip it.
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# Optional: Mapbox token for nicer basemap tiles in the frontend.
# If left blank, the frontend automatically falls back to free OpenStreetMap
# tiles (no key required) -- see frontend/static/js/app.js -> TILE_CONFIG.
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "")

# Keyless satellite imagery basemap. This is satellite imagery similar in use to
# a Google-Earth-style map view, but it is not Google Earth/3D imagery.
SATELLITE_TILE_URL = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
SATELLITE_ATTRIBUTION = "&copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community"

# --- Risk engine tuning ---
# How often (seconds) the frontend should re-poll /api/risk-data
REFRESH_INTERVAL_SECONDS = int(os.getenv("REFRESH_INTERVAL_SECONDS", 300))

# Simple in-memory cache TTL for upstream API calls, to avoid hammering
# Open-Meteo and to keep the dashboard fast for a live demo.
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 180))
