# API Reference

All endpoints are served by `backend/app.py` on `http://localhost:5000` (or whatever `PORT`
you set in `.env`). All responses are JSON unless noted.

---

## `GET /api/health`

Simple liveness check.

```json
{ "status": "ok", "locations_loaded": 25 }
```

---

## `GET /api/locations`

Static list of every monitored settlement (no live data, fast).

```json
{
  "count": 25,
  "locations": [
    {
      "id": "uk-joshimath",
      "name": "Joshimath (Chamoli)",
      "state": "Uttarakhand",
      "district": "Chamoli",
      "lat": 30.559, "lon": 79.5641,
      "elevation_m": 1875,
      "slope_class": "Very High",
      "soil_type": "Old landslide debris, subsidence-prone",
      "river_basin": "Alaknanda",
      "historical_events": 13
    }
  ]
}
```

---

## `GET /api/config`

Public, non-secret config the frontend needs at boot.

```json
{ "mapbox_access_token": "", "refresh_interval_seconds": 300 }
```

`mapbox_access_token` is empty unless you set `MAPBOX_ACCESS_TOKEN` in `.env` — the frontend
falls back to free OpenStreetMap tiles automatically when it's empty.

---

## `GET /api/risk-data`

Live risk score for **every** location, sorted highest-risk first. This is what powers the
map pins and the sidebar watchlist. Internally this calls Open-Meteo once per location
(subject to the server-side cache — see `CACHE_TTL_SECONDS`).

```json
{
  "count": 25,
  "results": [
    {
      "id": "uk-joshimath",
      "name": "Joshimath (Chamoli)",
      "state": "Uttarakhand",
      "district": "Chamoli",
      "lat": 30.559, "lon": 79.5641,
      "risk": {
        "score": 42.3,
        "level": "orange",
        "label": "Warning",
        "color": "#E07A1F",
        "description": "Risk rising quickly...",
        "factors": {
          "rainfall_subscore": 38.1,
          "soil_subscore": 55.0,
          "slope_subscore": 100,
          "history_subscore": 100
        },
        "live": {
          "rainfall_last_hour_mm": 2.1,
          "rainfall_next_6h_mm": 18.4,
          "rainfall_next_24h_mm": 41.2,
          "max_hourly_intensity_mm": 6.7,
          "soil_moisture_0_7cm": 0.31,
          "soil_moisture_7_28cm": 0.29,
          "temperature_c": 14.2,
          "weather_code": 61,
          "source": "open-meteo-live",
          "fetched_at": 1730000000
        }
      }
    }
  ]
}
```

---

## `GET /api/risk-data/<location_id>`

Same shape as one item above, plus terrain reference fields (`river_basin`, `slope_class`,
`soil_type`). Used by the detail drawer when you click a marker or watchlist row.

`404` if `<location_id>` isn't in `data/locations.json`:
```json
{ "error": "Unknown location id 'xyz'" }
```

---

## `POST /api/chatbot`

**Request body:**
```json
{ "message": "what should be in my emergency kit?" }
```

**Response:**
```json
{ "reply": "A basic go-bag should have: torch with spare batteries, ...", "matched_id": "emergency-kit" }
```

`matched_id` is `null` when no keyword matched well enough and the default fallback answer was
returned — useful for logging "questions we couldn't answer" during testing, so you can expand
`data/knowledge_base.json`.

---

## `GET /api/chatbot/greeting`

Returns the opening message shown when the chat panel is first opened.
```json
{ "reply": "Namaste! I'm the Flash Flood Assist bot..." }
```

---

## `GET /api/soil-sample/<location_id>`

Returns the latest field soil photo for a location, if any.

No photo yet:
```json
{ "exists": false }
```

Photo present:
```json
{
  "exists": true,
  "location_id": "hp-kullu",
  "filename": "sample.jpg",
  "uploaded_at": 1730000000,
  "image_url": "/api/soil-sample/hp-kullu/image",
  "analysis": {
    "avg_brightness": 45.3,
    "avg_rgb": [61.0, 45.0, 30.0],
    "moisture_hint": "dark",
    "label": "Looks dark - visually consistent with moist/saturated soil",
    "tone_note": "reddish-brown tone"
  }
}
```

`404` if `<location_id>` isn't in `data/locations.json`.

## `POST /api/soil-sample/<location_id>`

Multipart form upload, field name **`photo`** (JPG/PNG/WEBP, max 8MB). Overwrites any
previous photo for that location. Returns the same shape as the GET above.

## `GET /api/soil-sample/<location_id>/image`

Serves the raw photo file. `404` if none uploaded yet.

> **Important:** `analysis` is a transparent visual heuristic (average brightness/tone of the
> photo), not a calibrated soil-moisture sensor reading. See `backend/soil_sample.py`'s
> docstring and `docs/DATA_SOURCES.md` for the upgrade path to a real trained image model.

---

## Risk score formula (for reference)

```
score = 0.45 * rainfall_subscore
      + 0.25 * soil_subscore
      + 0.20 * slope_subscore
      + 0.10 * history_subscore
```

- `rainfall_subscore` — blends peak hourly intensity (50%), next-6h accumulation (30%), and
  next-24h accumulation (20%), each normalised against approximate IMD heavy-rainfall
  thresholds. See `risk_engine._rainfall_score()`.
- `soil_subscore` — weighted average of 0–7cm and 7–28cm modelled soil moisture, normalised
  against typical saturation (~0.45 m³/m³). See `risk_engine._soil_score()`.
- `slope_subscore` — static lookup from `slope_class` (Low=10, Moderate=40, High=70, Very
  High=100).
- `history_subscore` — static, scaled from `historical_events` in `data/locations.json`
  (max reference value 13).

All four are combined and clamped to `[0, 100]`, then mapped to a band via
`risk_engine.ALERT_BANDS`.
