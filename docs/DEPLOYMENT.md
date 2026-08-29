# Deployment (beyond localhost)

For SIH judging you may want a link you can open on any device, not just `localhost`. A few
free/low-friction options, roughly easiest first:

## Option A — Localtunnel / ngrok (fastest, good for a demo day)

```bash
python run.py
# in a second terminal:
npx localtunnel --port 5000
# or, if you have ngrok installed:
ngrok http 5000
```
Gives you a temporary public URL that tunnels to your laptop. Good for a live demo, not for a
permanent link.

## Option B — Render.com / Railway.app free tier (permanent link)

Both platforms can run a Flask app directly from a GitHub repo:

1. Push this project to a GitHub repository.
2. Create a new "Web Service" (Render) or project (Railway), point it at the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `python run.py` (or `gunicorn backend.app:app` for a more production-ready
   server — add `gunicorn` to `requirements.txt` if you use this).
5. Add your `.env` values as environment variables in the platform's dashboard (never commit
   `.env` itself).

## Option C — PythonAnywhere (simple, free tier, good for students)

PythonAnywhere's free tier can host a small Flask app directly with a WSGI config pointing at
`backend.app:app`. Good if your team wants a stable link without a credit card.

## Production hardening checklist (optional, if you go beyond a hackathon demo)

- Swap Flask's built-in dev server for `gunicorn` or `waitress`.
- Set `FLASK_ENV=production` in `.env` (disables debug mode).
- Add rate limiting in front of `/api/risk-data` if you expect real public traffic (Open-Meteo
  has fair-use limits).
- Move `data/locations.json` into a real database once you have more than a few hundred
  settlements, and add an admin flow to manage it instead of hand-editing JSON.
- Add authenticated ingestion endpoints for real IoT sensor data (see `docs/DATA_SOURCES.md`).
