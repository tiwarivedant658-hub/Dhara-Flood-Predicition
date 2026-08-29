# File-by-file guide

A short description of every file in this project, so any teammate can find their way around
without reading all the code first.

## Root

| File | Purpose |
|---|---|
| `run.py` | Single command to start the whole app (`python run.py`). |
| `requirements.txt` | Python dependencies (Flask, Flask-Cors, requests, python-dotenv). |
| `.env.example` | Every configurable setting, documented inline. Copy to `.env`. |
| `.env` | Your local copy of the above (git-ignored, created during setup). |
| `.gitignore` | Keeps `.env`, `__pycache__`, virtual envs, etc. out of version control. |
| `README.md` | Start here — setup, run instructions, overview. |

## `backend/`

| File | Purpose |
|---|---|
| `app.py` | Flask app: registers all `/api/...` routes and serves the frontend files. |
| `config.py` | Reads `.env` into typed constants used everywhere else. |
| `data_fetcher.py` | Calls the live Open-Meteo API for a lat/lon; caches + fails soft. |
| `risk_engine.py` | Turns live + static data into a 0–100 score and 5-band alert. |
| `chatbot.py` | Keyword-matching chatbot logic over `data/knowledge_base.json`. |
| `__init__.py` | Makes `backend/` an importable Python package. |

## `frontend/`

| File | Purpose |
|---|---|
| `index.html` | The single page — header, map, sidebar, detail drawer, chat widget. |
| `static/css/style.css` | All styling. Design-token comment block at the top explains the colour/type system: warm off-white background, deep forest-teal brand colour (`--ridge`), Fraunces display serif + IBM Plex Sans body + IBM Plex Mono for data/numbers. Deliberately avoids dark backgrounds and the generic "AI purple-blue gradient" look — palette is grounded in terrain/topographic-map references instead. |
| `static/js/app.js` | Boots the Leaflet map, polls `/api/risk-data`, renders markers/sidebar/detail drawer. |
| `static/js/chatbot.js` | Floating chat widget: open/close, send message, render replies. |

## `data/`

| File | Purpose |
|---|---|
| `locations.json` | The 25 monitored settlements (HP/J&K/Ladakh/Uttarakhand) with coordinates and static terrain reference fields. See its own `_readme` key and `docs/DATA_SOURCES.md`. |
| `knowledge_base.json` | The chatbot's content — keyword → answer pairs. Edit this file to teach the bot new answers; no code changes needed. |

## `docs/`

| File | Purpose |
|---|---|
| `ARCHITECTURE.md` | System diagram, request flow, why this stack, where ML would plug in. |
| `API.md` | Every endpoint's request/response shape + the exact risk-score formula. |
| `DATA_SOURCES.md` | What's genuinely live vs. illustrative/static today, and how to upgrade each piece for a production deployment. |
| `FILE_GUIDE.md` | This file. |
| `DEPLOYMENT.md` | How to host this beyond `localhost` for a live/remote demo. |

## Design rationale (for the UI specifically)

The brief asked for something that looks intentionally designed, not templated, with **no dark
background** and **no purple/blue "AI" gradient**. The chosen direction:

- **Background** stays a warm-cool off-white paper tone (`--paper: #F4F5EF`) throughout —
  never dark.
- **Brand colour** is a deep forest/spruce teal (`--ridge: #2F5D50`) — pulled from the
  Himalayan hill-forest setting the system monitors, not a generic tech gradient.
- **Alert colours** (green/yellow/orange/red/maroon) are the only saturated colours in the UI,
  so they read unambiguously as *the* signal to watch — everything else (chrome, cards, text)
  stays quiet and neutral by comparison.
- **Signature element:** a subtle hand-drawn contour-line watermark in the header
  (`.contour-watermark` in `style.css`), referencing topographic relief maps of hilly terrain —
  tying the one decorative flourish directly back to the problem domain instead of being pure
  decoration.
- **Typography:** Fraunces (a warm serif with real personality) for headings, IBM Plex Sans for
  body copy, and IBM Plex Mono specifically for numeric readouts (scores, mm of rain, percent
  soil moisture) so data reads as data at a glance.
