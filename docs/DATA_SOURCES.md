# Data Sources — what's live, what's static, and how to upgrade each

Being explicit about this is important for judge Q&A — nothing here pretends to be more real
than it is.

## 1. LIVE today: rainfall + soil moisture (Open-Meteo)

- **Provider:** [open-meteo.com](https://open-meteo.com/) — free, no API key, no signup,
  generous rate limits for non-commercial use.
- **Called from:** `backend/data_fetcher.py::fetch_live_conditions(lat, lon)`
- **What we pull:** hourly `precipitation`, `soil_moisture_0_to_7cm`,
  `soil_moisture_7_to_28cm`, `temperature_2m`, `weathercode`, for 1 day in the past and 2 days
  forecast, for the exact lat/lon of each settlement.
- **Refresh:** every time `/api/risk-data` is called, subject to an in-process cache
  (`CACHE_TTL_SECONDS`, default 180s) to avoid re-fetching the same coordinate too often.
- **Upgrade path — IoT sensors:** once your team has real river-gauge / rain-gauge / soil
  sensors, stand up a small ingestion endpoint (e.g. `POST /api/ingest/<sensor_id>`, MQTT
  bridge, or a scheduled job) that writes into the same in-memory cache structure used by
  `_cache` in `data_fetcher.py`, or — cleaner — add a second function
  `fetch_sensor_conditions(sensor_id)` and have `fetch_live_conditions()` prefer sensor data
  over Open-Meteo when a sensor exists for that location. The rest of the pipeline
  (`risk_engine.py`, the API, the frontend) doesn't need to change at all, because they only
  depend on the returned dict's shape, not where it came from.

## 2. STATIC today: slope stability, soil type, historical hazard frequency

- **Where:** `data/locations.json` (`slope_class`, `soil_type`, `historical_events`,
  `river_basin`, `elevation_m`)
- **What it actually is:** illustrative baseline values, set from general public knowledge of
  which districts/towns in these four states are commonly cited as landslide/flash-flood
  hazard zones (e.g. Kishtwar, Joshimath, Rudraprayag, Kinnaur, Nainital are widely documented
  high-hazard areas). They are **not** pulled from a live geological survey.
- **Upgrade path:**
  - **Slope stability:** replace with actual DEM-derived slope angle + a stability index from
    [GSI Bhukosh](https://bhukosh.gsi.gov.in/) or a computed slope raster (e.g. from SRTM/
    Cartosat DEM tiles) sampled at each settlement's coordinates.
  - **Historical landslide/flood inventory:** replace `historical_events` with a real count
    from the [NDMA](https://ndma.gov.in/) or state Disaster Management Authority incident
    databases, or the Geological Survey of India's Landslide Inventory.
  - Both changes are localized to `data/locations.json` — no code changes needed in
    `risk_engine.py` as long as you keep the same field names and roughly the same value
    ranges (or adjust the normalisation constants in `risk_engine.SLOPE_SCORE` /
    `_rainfall_score` accordingly).

## 3. Map tiles

- **Default:** OpenStreetMap raster tiles — free, keyless, no signup.
- **Optional upgrade:** set `MAPBOX_ACCESS_TOKEN` in `.env` (free tier, no credit card) for
  Mapbox's "Outdoors" terrain style, which renders contour lines and hillshading — a nice fit
  for this problem statement. The frontend (`app.js`) automatically switches to it once the
  token is present in `/api/config`.

## 4. Chatbot content

- **Where:** `data/knowledge_base.json`
- **What it is:** hand-curated prevention/preparedness guidance (general disaster-management
  best practice: NDMA-style dos and don'ts, go-bag contents, alert-colour meanings). It is a
  static rule-based knowledge base, not a live/generative model — see `docs/API.md` and
  `backend/chatbot.py` for why, and how to swap it for an LLM later if you want.

## 5. Field soil photos (new)

- **Where:** `backend/soil_sample.py`, storage at `data/soil_samples/<location_id>/`
  (git-ignored — these are user-uploaded, not source data).
- **What it is today:** a volunteer/field user can attach one photo per location (camera
  capture on mobile, or file upload on desktop) from the "Field Soil Sample" section of the
  detail drawer. The backend runs a small, transparent heuristic — average brightness and
  rough colour tone of the photo — and buckets it into a qualitative label ("looks dark &
  likely moist" / "looks pale & likely dry"). This is clearly labelled in the UI as a visual
  heuristic, **not** a calibrated moisture sensor reading.
- **Upgrade path:** replace `soil_sample.analyze_image()` with a call to a trained image
  classifier (e.g. a small CNN fine-tuned on labelled soil-moisture photographs) that returns
  a calibrated estimate instead of a brightness heuristic. Keep the same return-dict shape
  (or extend it) and nothing else in the API/frontend needs to change. You could also extend
  storage to keep a history of samples per location instead of just the latest one.

## 6. Coordinates

- **Where:** `data/locations.json`
- Approximate town/city-centre coordinates for 25 settlements across the 4 states (6-7 per
  state), covering a mix of state capitals, well-known hazard-prone towns, and remote/high
  altitude settlements (e.g. Ladakh's Nubra and Zanskar valleys). For a real village/ward-level
  system (as the problem statement asks), extend this file with your target villages' actual
  coordinates — the whole pipeline scales to any number of entries automatically.

## Predictive training data contract

The operational demo uses live Open-Meteo precipitation/soil moisture and a prototype predictive calibration model. The research version should train on India-specific labelled events from IMD rainfall, MOSDAC/ISRO soil wetness, DEM-derived terrain, Bhuvan/NRSC spatial layers, and verified GSI/historical flood/landslide event inventories. The prediction target should be explicitly defined, e.g. whether a verified trigger event occurs in the next six hours for a 1 km cell.
