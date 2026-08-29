# Architecture

## Why this stack

- **Python (Flask) backend**, not just HTML/CSS/JS: the problem statement asks for a
  *predictive system* combining multiple data sources — that scoring/fusion logic belongs on
  a server, testable in isolation from the UI, and swappable for a real ML model later without
  touching the frontend at all.
- **Vanilla HTML/CSS/JS frontend** (no build step): the whole app runs from `python run.py`
  with nothing to compile — important when you're demoing on a venue laptop with patchy wifi.
- **Leaflet.js + OpenStreetMap**: free, keyless, battle-tested map library. No API key means
  no "it worked on my laptop but not on stage" risk.
- **Open-Meteo** as the live weather/soil-moisture provider: free, keyless, and — critically —
  exposes modelled soil moisture at depth, which most free weather APIs don't.

## Request flow

```
 Browser (frontend/)
     │
     │ GET /                       → index.html
     │ GET /static/css|js/*        → styling + map/chatbot logic
     │
     │ GET /api/locations          → static settlement list (25 places, 4 states)
     │ GET /api/config             → optional Mapbox token, refresh interval
     │ GET /api/risk-data          → risk score for ALL locations (map + sidebar)
     │ GET /api/risk-data/<id>     → risk score + full breakdown (detail drawer)
     │ POST /api/chatbot           → { message } → { reply }
     ▼
 Flask app (backend/app.py)
     │
     ├─ data/locations.json  ──────────► static terrain reference data
     │
     ├─ backend/data_fetcher.py ───────► LIVE call to Open-Meteo per location
     │        (in-memory cache, TTL from .env, fails soft on network errors)
     │
     ├─ backend/risk_engine.py ────────► combines live + static data → 0-100 score,
     │                                    5-band alert classification, factor breakdown
     │
     └─ backend/chatbot.py ────────────► keyword match against data/knowledge_base.json
```

## Data refresh model

The frontend polls `/api/risk-data` every `REFRESH_INTERVAL_SECONDS` (default 300s / 5 min).
The backend itself caches each location's Open-Meteo response for `CACHE_TTL_SECONDS`
(default 180s) so that multiple browser tabs / judges refreshing the page don't hammer the
upstream API or blow past its fair-use limits during a demo.

## Where an ML model would slot in

Today `risk_engine.compute_risk()` is a transparent weighted-sum model — deliberately, so it's
explainable in a judge Q&A. To upgrade it to a trained model (e.g. a gradient-boosted classifier
or a small neural net) without touching the frontend or API contract:

1. Train the model offline using historical rainfall/soil/slope data labelled with actual
   flood/no-flood outcomes.
2. Replace the body of `compute_risk()` with a call to your model (`model.predict_proba(...)`),
   still returning the same `{score, level, label, color, description, factors, live}` shape.
3. Everything downstream (API responses, map colours, chatbot) keeps working unchanged.

## Frontend structure

- `frontend/static/js/app.js` — map, live data polling, sidebar, detail drawer.
- `frontend/static/js/chatbot.js` — floating chat widget, independent of `app.js`.
- `frontend/static/css/style.css` — all styling; see the token comment block at the top for
  the full colour/type system and the reasoning behind it (see also `docs/FILE_GUIDE.md`).

No frontend framework/build step is used on purpose — for a solo-viewable hackathon demo, one
`<script>` per concern is easier to explain live than a bundler config.

## Predictive engine (v4+)

DHARA now exposes a six-hour flash-flood prediction layer. The backend collects recent and forecast precipitation plus shallow/mid-depth soil moisture, builds derived temporal features, and feeds them to a Random Forest classifier. The API returns probability, prediction band, estimated trigger lead time, top model drivers, and data-completeness confidence.

The bundled classifier is a **prototype calibration model** trained on physics-informed synthetic storm scenarios so the application remains runnable without a large research dataset. It is not field-validated. For an SIH/research claim, replace it with a chronological IMD + MOSDAC + DEM + Bhuvan/GSI labelled event dataset using `scripts/train_model.py`, then report precision, recall, F1, ROC-AUC, false-alarm rate and warning lead time.
