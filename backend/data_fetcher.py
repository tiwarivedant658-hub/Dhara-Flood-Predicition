"""
data_fetcher.py
----------------
Talks to the live weather/soil-moisture data source (Open-Meteo) for a given
lat/lon and returns a normalised dict the risk engine can consume.

Why Open-Meteo: it is free, requires NO API key/signup, has generous rate
limits for non-commercial/hackathon use, and exposes both a rainfall
forecast AND modelled soil moisture at multiple depths for any point on
Earth -- which is exactly the "rainfall + soil moisture" combination the
problem statement asks for. See docs/DATA_SOURCES.md for details and for
how to swap in IoT sensor feeds or a paid provider later.

A tiny in-memory cache avoids re-fetching the same location within
CACHE_TTL_SECONDS, which keeps the live map fast and avoids rate-limit
issues during a demo.
"""

import time
from datetime import datetime, timedelta, timezone

import requests
from backend import config

_cache: dict[str, tuple[float, dict]] = {}


def _get_cached(key: str):
    entry = _cache.get(key)
    if not entry:
        return None
    fetched_at, data = entry
    if time.time() - fetched_at > config.CACHE_TTL_SECONDS:
        return None
    return data


def _set_cache(key: str, data: dict):
    _cache[key] = (time.time(), data)


def fetch_live_conditions(lat: float, lon: float) -> dict:
    """
    Fetch current + short-term-forecast rainfall and soil moisture for a
    coordinate from Open-Meteo.

    Returns a dict like:
    {
        "rainfall_last_hour_mm": float,
        "rainfall_next_6h_mm": float,
        "rainfall_next_24h_mm": float,
        "max_hourly_intensity_mm": float,
        "soil_moisture_0_7cm": float,   # m3/m3, 0-1 range
        "soil_moisture_7_28cm": float,
        "temperature_c": float,
        "weather_code": int,
        "source": "open-meteo-live" | "open-meteo-unreachable"
    }

    On network failure it returns zeroed-out data with source flagged, so the
    risk engine can fall back gracefully instead of crashing the whole
    dashboard (important for a live demo on flaky venue wifi).
    """
    cache_key = f"{round(lat, 3)},{round(lon, 3)}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "precipitation",
            "soil_moisture_0_to_7cm",
            "soil_moisture_7_to_28cm",
            "temperature_2m",
            "weather_code",
        ]),
        "forecast_days": 2,
        "past_days": 3,
        "timezone": "auto",
    }

    try:
        resp = requests.get(config.OPEN_METEO_FORECAST_URL, params=params, timeout=8)
        resp.raise_for_status()
        raw = resp.json()
        hourly = raw.get("hourly", {})

        precip = hourly.get("precipitation", []) or []
        soil_shallow = hourly.get("soil_moisture_0_to_7cm", []) or []
        soil_mid = hourly.get("soil_moisture_7_to_28cm", []) or []
        temps = hourly.get("temperature_2m", []) or []
        codes = hourly.get("weather_code", []) or []
        times = hourly.get("time", []) or []

        # Open-Meteo returns past_days + forecast_days of hourly data in one
        # array. We locate "now" as the index closest to len(past)*24.
        now_idx = _find_now_index(times, raw.get("utc_offset_seconds", 0))

        rainfall_last_hour = _safe_get(precip, now_idx, default=0.0)
        rainfall_prev_1h = _safe_get(precip, now_idx - 1, default=0.0)
        rainfall_last_3h = sum(_safe_get(precip, now_idx - i, 0.0) for i in range(1, 4))
        rainfall_last_6h = sum(_safe_get(precip, now_idx - i, 0.0) for i in range(1, 7))
        rainfall_last_24h = sum(_safe_get(precip, now_idx - i, 0.0) for i in range(1, 25))
        rainfall_last_72h = sum(_safe_get(precip, now_idx - i, 0.0) for i in range(1, 73))
        rainfall_next_6h = sum(_safe_get(precip, now_idx + i, 0.0) for i in range(0, 6))
        rainfall_next_24h = sum(_safe_get(precip, now_idx + i, 0.0) for i in range(0, 24))
        max_hourly_intensity = max(precip[max(0, now_idx - 6):now_idx + 24] or [0.0])
        forecast_hourly_precipitation = [_safe_get(precip, now_idx + i, 0.0) for i in range(0, 12)]

        data = {
            "rainfall_last_hour_mm": round(rainfall_last_hour, 2),
            "rainfall_prev_1h_mm": round(rainfall_prev_1h, 2),
            "rainfall_last_3h_mm": round(rainfall_last_3h, 2),
            "rainfall_last_6h_mm": round(rainfall_last_6h, 2),
            "rainfall_last_24h_mm": round(rainfall_last_24h, 2),
            "rainfall_last_72h_mm": round(rainfall_last_72h, 2),
            "rainfall_next_6h_mm": round(rainfall_next_6h, 2),
            "rainfall_next_24h_mm": round(rainfall_next_24h, 2),
            "max_hourly_intensity_mm": round(max_hourly_intensity, 2),
            "soil_moisture_0_7cm": _safe_get(soil_shallow, now_idx, 0.2),
            "soil_moisture_7_28cm": _safe_get(soil_mid, now_idx, 0.2),
            "soil_moisture_prev": _safe_get(soil_shallow, now_idx - 1, None),
            "forecast_hourly_precipitation": forecast_hourly_precipitation,
            "temperature_c": _safe_get(temps, now_idx, None),
            "weather_code": _safe_get(codes, now_idx, None),
            "source": "open-meteo-live",
            "fetched_at": int(time.time()),
        }
        _set_cache(cache_key, data)
        return data

    except (requests.RequestException, ValueError, KeyError, TypeError):
        # Network unavailable (e.g. offline demo). Fail soft.
        fallback = {
            "rainfall_last_hour_mm": 0.0,
            "rainfall_prev_1h_mm": 0.0,
            "rainfall_last_3h_mm": 0.0,
            "rainfall_last_6h_mm": 0.0,
            "rainfall_last_24h_mm": 0.0,
            "rainfall_last_72h_mm": 0.0,
            "rainfall_next_6h_mm": 0.0,
            "rainfall_next_24h_mm": 0.0,
            "max_hourly_intensity_mm": 0.0,
            "soil_moisture_0_7cm": 0.2,
            "soil_moisture_7_28cm": 0.2,
            "soil_moisture_prev": 0.2,
            "forecast_hourly_precipitation": [],
            "temperature_c": None,
            "weather_code": None,
            "source": "open-meteo-unreachable",
            "fetched_at": int(time.time()),
        }
        return fallback


def _find_now_index(times: list[str], utc_offset_seconds: int = 0) -> int:
    """Return the hourly entry closest to the current local time.

    Open-Meteo returns local ISO timestamps when ``timezone=auto`` is used.
    The previous implementation always chose index 24, which is midnight
    today and can be many hours away from the real current hour.
    """
    if not times:
        return 0

    target = datetime.now(timezone.utc) + timedelta(seconds=utc_offset_seconds or 0)
    target = target.replace(tzinfo=None)

    parsed = []
    for i, value in enumerate(times):
        try:
            parsed.append((i, datetime.fromisoformat(value).replace(tzinfo=None)))
        except (TypeError, ValueError):
            continue

    if not parsed:
        return min(24, max(0, len(times) - 1))

    return min(parsed, key=lambda item: abs(item[1] - target))[0]


def _safe_get(lst: list, idx: int, default):
    if 0 <= idx < len(lst) and lst[idx] is not None:
        return lst[idx]
    return default
