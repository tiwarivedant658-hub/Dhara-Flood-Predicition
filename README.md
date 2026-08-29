# Dhara — Flash Flood Early Warning System
### Smart India Hackathon · Problem Statement 192 — AI-based Flash Flood Prediction

A hyper-local flash flood prediction dashboard for the hill states **Himachal Pradesh, Jammu & Kashmir,
Ladakh and Uttarakhand**. It combines **live rainfall + soil moisture data**, static
**slope-stability / terrain** baselines, and **historical hazard frequency** into a single
0–100 prediction score per settlement, shown on an interactive map with a 5-band colour alert
system, plus a built-in chatbot for prevention and preparedness questions.

> Built as a hackathon prototype. Every "why this looks the way it does" decision is explained
> in `docs/` — read those before your judging round.

---

## 9. Historical multi-source DHARA training

This build now contains a real-data training/validation pipeline:

`IMD rainfall + MOSDAC soil wetness + Bhuvan terrain/flood layers + GSI verified events`
→ `labelled training_data.csv` → `Random Forest DHARA` → **chronological 80/20 validation**
→ Precision / Recall / F1 / ROC-AUC / PR-AUC / False Alarm Rate / warning lead time.

The application automatically loads `data/research/dhara_model.joblib` when it exists.
Without that artifact it keeps the clearly-labelled synthetic prototype fallback so the
demo still starts.

### One-time historical-data workflow

1. Download/export the four source families using `data/research/DATA_ACQUISITION.md`.
2. Put normalized CSVs in `data/research/raw/`.
3. Build the labelled dataset:
   `python scripts/build_dataset.py --imd data/research/raw/imd.csv --mosdac data/research/raw/mosdac.csv --terrain data/research/raw/terrain.csv --bhuvan data/research/raw/bhuvan.csv --gsi data/research/raw/gsi.csv`
4. Train and validate:
   `python scripts/train_model.py`
5. Open `data/research/validation_metrics.json` and use those values in the SIH report.
6. Restart the web app. The prediction API will report `model_source: validated_historical`.

**Do not invent or manually type Precision/Recall/F1/AUC.** They are generated from the
chronological held-out period. If the dataset is too small to contain both classes in
the future test period, the training script stops rather than producing misleading metrics.


## 1. What's inside

```
flash-flood-prediction-sih192/
├── backend/                 Python (Flask) API + prediction engine + chatbot
│   ├── app.py                Flask routes (serves API + the frontend)
│   ├── config.py              Loads .env into constants
│   ├── data_fetcher.py         Live rainfall/soil-moisture from Open-Meteo
│   ├── prediction_engine.py           Weighted prediction-scoring model
│   ├── chatbot.py                 Rule-based Q&A engine
│   └── requirements.txt (see root)
├── frontend/                 Static site served by Flask
│   ├── index.html
│   └── static/{css,js}
├── data/                     Source-of-truth data files
│   ├── locations.json         25 settlements across the 4 states (lat/lon + terrain)
│   └── knowledge_base.json     Chatbot's prevention/preparedness content
├── docs/                     Full documentation (architecture, API, data sources)
├── run.py                    Single command to start everything
├── requirements.txt
├── .env.example               Copy to .env — every variable documented inline
└── .gitignore
```

## 2. Quick start (3 commands)

**Requirements:** Python 3.10+ and an internet connection (for live weather data).

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment file (defaults work out of the box — no keys required)
cp .env.example .env

# 3. Run the app
python run.py
```

Then open **http://localhost:5000** in your browser. That's it — one server serves both the
API and the UI, so there's nothing else to start.

> Using a fresh machine? Create a virtual environment first:
> `python -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`)
> then run the 3 commands above.

## 3. Where does the "real-time" data come from?

We deliberately use **[Open-Meteo](https://open-meteo.com/)** as the live data source because
it needs **zero API key / zero signup** and gives us both rainfall forecasts *and* modelled
soil moisture (0–7cm and 7–28cm depth) for any coordinate — exactly the two live inputs the
problem statement asks for. `backend/data_fetcher.py` calls it live, every time the map
refreshes (default: every 5 minutes, see `REFRESH_INTERVAL_SECONDS` in `.env`).

There is **no real IoT sensor network or paid maps API key bundled** — a hackathon team
cannot ship physical sensors or a company credit card in a zip file. Instead:

- **Map tiles**: free, keyless OpenStreetMap tiles by default (`frontend/static/js/app.js`).
  If you obtain a free Mapbox token (no card required, see `.env.example`), drop it into
  `.env` and the map automatically upgrades to Mapbox's terrain basemap — no code changes.
- **IoT sensors**: `docs/DATA_SOURCES.md` explains exactly where in `data_fetcher.py` to plug
  in real gauge/sensor telemetry (e.g. via MQTT → a small ingestion endpoint → the same
  `fetch_live_conditions()` contract) once your team has hardware.
- **Slope stability / historical landslide data**: currently static, clearly-labelled
  reference values in `data/locations.json` (see the `_readme` key in that file). Swap in
  GSI Bhukosh / NDMA datasets before treating this as production-accurate.

This keeps the demo **fully live and functional today**, while being explicit about what's a
placeholder vs. what's real — important for judge Q&A.

## 4. How the prediction score works

See `backend/prediction_engine.py` (heavily commented) and `docs/API.md` for the full formula.
Short version — four weighted factors combine into one 0–100 score:

| Factor | Weight | Source |
|---|---|---|
| Rainfall intensity + 6h/24h accumulation | 45% | Live, Open-Meteo |
| Soil moisture / saturation | 25% | Live, Open-Meteo |
| Slope stability class | 20% | Static terrain reference |
| Historical hazard frequency | 10% | Static terrain reference |

The score maps to 5 colour bands (same colours drive the map pins, sidebar and detail drawer):

| Score | Band | Colour | Meaning |
|---|---|---|---|
| 0–20 | Safe | Green `#2E7D4F` | Normal monitoring |
| 20–40 | Watch | Yellow `#D9A400` | Conditions building |
| 40–60 | Warning | Orange `#E07A1F` | Prepare to move |
| 60–80 | Danger | Red `#C13B2E` | Evacuate now |
| 80–100 | Severe | Maroon `#7A2020` | Life-threatening |

## 5. The chatbot

Bottom-right "Ask about flash floods" button. It's a **rule-based** engine
(`backend/chatbot.py` + `data/knowledge_base.json`) covering: alert colour meanings,
emergency kit contents, before/during/after-flood actions, causes, warning signs, GLOFs,
and helpline numbers. No external API key needed, works offline. See `docs/API.md` for how
to extend it, or swap it for an LLM later.

## 6. Documentation

| File | What it covers |
|---|---|
| `docs/ARCHITECTURE.md` | System diagram, request flow, why Flask+vanilla JS |
| `docs/API.md` | Every backend endpoint, request/response shape, prediction formula |
| `docs/DATA_SOURCES.md` | What's live vs static today, and how to upgrade each one |
| `docs/FILE_GUIDE.md` | What every single file in this repo does |
| `docs/DEPLOYMENT.md` | Options to host this beyond `localhost` for a live demo |

## 7. Troubleshooting

- **Map pins are all yellow/grey with 0mm rain everywhere** → your machine likely can't reach
  `api.open-meteo.com` (offline, or a restrictive firewall/proxy). The app fails soft, not
  hard — check `/api/health` and the browser console for `unreachable` in the prediction data.
- **`ModuleNotFoundError`** → you forgot `pip install -r requirements.txt`, or you're not in
  the project's virtual environment.
- **Port 5000 already in use** → change `PORT` in `.env`, then restart `python run.py`.

---
Made for SIH PS 192 — Flash Flood Prediction System for Hilly Regions using Multi-Source Data.

## 8. Latest UI update

The current build keeps the original Dhara colour grading and adds:

- a reliable close control for Flash Flood Assist (click `×` or press Escape),
- a more visible field-photo workflow,
- upload support for soil, terrain/slope, river/drainage, land use/vegetation and flood evidence,
- image preview before/while uploading,
- a prediction-score bar chart,
- an alert-band pie chart,
- more human-centred dashboard wording without changing the core visual theme,
- satellite context through the existing Esri World Imagery layer.

The full technical documentation is available in:

- `docs/FULL_DOCUMENTATION.md`
- `docs/Dhara_Full_Project_Documentation.pdf`


## Predictive web mode

The application now exposes a six-hour **flash-flood trigger probability** through `/api/prediction/<location_id>` and the existing `/api/risk-data` endpoint. The UI displays probability, forecast trajectory, estimated trigger lead time, input completeness confidence, and top model drivers.

The bundled Random Forest is a **prototype calibration model** trained on physics-informed synthetic storm scenarios so the project runs immediately. It is not field-validated and must not be presented as measured operational accuracy. For SIH/research validation, replace the calibration data with labelled Indian observations using the contract in `data/research/README.md` and the training workflow in `scripts/train_model.py`.
