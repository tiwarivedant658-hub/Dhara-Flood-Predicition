"""
app.py
------
Flask entry point. Wires together:
  - static file serving for the frontend (frontend/)
  - /api/locations        -> static list of monitored settlements
  - /api/risk-data        -> LIVE risk score for every settlement (map data)
  - /api/risk-data/<id>   -> LIVE risk score + factor breakdown for one place
  - /api/chatbot          -> POST a message, get a prevention/info reply
  - /api/health           -> simple uptime/status check

Run with:  python run.py   (see README.md / docs for full setup)
"""

import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS

from backend import config, chatbot, soil_sample, evidence
from backend.data_fetcher import fetch_live_conditions
from backend.risk_engine import compute_risk
from backend.predictive_engine import predict
from backend.report import build_report

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
LOCATIONS_PATH = BASE_DIR / "data" / "locations.json"
EMERGENCY_CONTACTS_PATH = BASE_DIR / "data" / "emergency_contacts.json"

app = Flask(__name__, static_folder=str(FRONTEND_DIR / "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = evidence.MAX_FILE_BYTES  # cap field evidence uploads at 8MB
CORS(app)

@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Image is too large. Maximum upload size is 8 MB."}), 413

with open(LOCATIONS_PATH, "r", encoding="utf-8") as f:
    _LOCATIONS = json.load(f)["locations"]

_LOCATIONS_BY_ID = {loc["id"]: loc for loc in _LOCATIONS}


# ---------------------------------------------------------------------------
# Frontend serving
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def frontend_files(filename):
    # Serves any other top-level frontend file if referenced directly.
    return send_from_directory(FRONTEND_DIR, filename)


# ---------------------------------------------------------------------------
# API: locations + config (so the frontend never hard-codes coordinates)
# ---------------------------------------------------------------------------

@app.route("/api/locations")
def get_locations():
    return jsonify({
        "count": len(_LOCATIONS),
        "locations": _LOCATIONS,
    })


@app.route("/api/config")
def get_public_config():
    """Non-secret config the frontend needs, e.g. optional Mapbox token.
    Never expose OPENWEATHER_API_KEY or any private key here."""
    return jsonify({
        "mapbox_access_token": config.MAPBOX_ACCESS_TOKEN,
        "satellite_tile_url": config.SATELLITE_TILE_URL,
        "satellite_attribution": config.SATELLITE_ATTRIBUTION,
        "refresh_interval_seconds": config.REFRESH_INTERVAL_SECONDS,
    })


# ---------------------------------------------------------------------------
# API: emergency contacts
# ---------------------------------------------------------------------------

@app.route("/api/emergency-contacts/<location_id>")
def get_emergency_contacts(location_id):
    loc = _LOCATIONS_BY_ID.get(location_id)
    if not loc:
        return jsonify({"error": f"Unknown location id '{location_id}'"}), 404
    with open(EMERGENCY_CONTACTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    contacts = list(data.get("national", []))
    state = data.get("states", {}).get(loc.get("state"), {})
    contacts.extend(state.get("state_contacts", []))
    district = state.get("districts", {}).get(loc.get("district"), {})
    if district.get("district_office"):
        contacts.append({"name": "District Disaster / Administration Office", "service": "District office / control room", "phone": district["district_office"], "type": "district"})
    if district.get("police"):
        contacts.append({"name": "Police / Emergency Response", "service": "Police control / emergency", "phone": district["police"], "type": "police"})
    seen=set(); unique=[]
    for c in contacts:
        key=(c.get("name"),c.get("phone"))
        if key not in seen:
            unique.append(c); seen.add(key)
    return jsonify({
        "location_id": location_id,
        "district": loc.get("district"),
        "state": loc.get("state"),
        "contacts": unique,
        "official_links": data.get("national_links", []) + state.get("official_links", []),
        "source_note": state.get("source_note", "Verify local contacts before operational use."),
    })

@app.route("/api/report/<location_id>")
def download_report(location_id):
    loc = _LOCATIONS_BY_ID.get(location_id)
    if not loc:
        return jsonify({"error": f"Unknown location id '{location_id}'"}), 404
    live = fetch_live_conditions(loc["lat"], loc["lon"])
    risk = compute_risk(loc, live)
    prediction = predict(loc, live)
    risk = {**risk, "prediction": prediction, "score": prediction["probability"], "label": prediction["label"], "level": prediction["level"], "description": prediction["description"]}
    report_path = build_report(loc, live, risk, evidence.list_for(location_id))
    return send_file(report_path, mimetype="application/pdf", as_attachment=True, download_name=f"Dhara_{loc['district'].replace(' ', '_')}_Risk_Report.pdf")

# ---------------------------------------------------------------------------
# API: live risk data
# ---------------------------------------------------------------------------

@app.route("/api/risk-data")
def get_all_risk_data():
    results = []
    for loc in _LOCATIONS:
        live = fetch_live_conditions(loc["lat"], loc["lon"])
        risk = compute_risk(loc, live)
        prediction = predict(loc, live)
        results.append({
            "id": loc["id"],
            "name": loc["name"],
            "state": loc["state"],
            "district": loc["district"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "risk": {**risk, "prediction": prediction, "score": prediction["probability"], "label": prediction["label"], "level": prediction["level"], "description": prediction["description"]},
            "prediction": prediction,
        })
    # Highest risk first, useful for a "top alerts" list in the UI.
    results.sort(key=lambda r: r["risk"]["score"], reverse=True)
    return jsonify({"count": len(results), "results": results})


@app.route("/api/risk-data/<location_id>")
def get_one_risk_data(location_id):
    loc = _LOCATIONS_BY_ID.get(location_id)
    if not loc:
        return jsonify({"error": f"Unknown location id '{location_id}'"}), 404
    live = fetch_live_conditions(loc["lat"], loc["lon"])
    risk = compute_risk(loc, live)
    prediction = predict(loc, live)
    return jsonify({
        "id": loc["id"],
        "name": loc["name"],
        "state": loc["state"],
        "district": loc["district"],
        "river_basin": loc.get("river_basin"),
        "slope_class": loc.get("slope_class"),
        "soil_type": loc.get("soil_type"),
        "elevation_m": loc.get("elevation_m"),
        "lat": loc["lat"],
        "lon": loc["lon"],
        "risk": {**risk, "prediction": prediction, "score": prediction["probability"], "label": prediction["label"], "level": prediction["level"], "description": prediction["description"]},
        "prediction": prediction,
    })


# ---------------------------------------------------------------------------
# API: predictive flash-flood forecast
# ---------------------------------------------------------------------------

@app.route("/api/prediction/<location_id>")
def get_prediction(location_id):
    loc = _LOCATIONS_BY_ID.get(location_id)
    if not loc:
        return jsonify({"error": f"Unknown location id '{location_id}'"}), 404
    live = fetch_live_conditions(loc["lat"], loc["lon"])
    return jsonify({
        "id": location_id,
        "name": loc["name"],
        "district": loc["district"],
        "state": loc["state"],
        "prediction": predict(loc, live),
    })


# ---------------------------------------------------------------------------
# API: chatbot
# ---------------------------------------------------------------------------

@app.route("/api/chatbot", methods=["POST"])
def chatbot_reply():
    body = request.get_json(silent=True) or {}
    message = body.get("message", "")
    result = chatbot.answer(message)
    return jsonify(result)


@app.route("/api/chatbot/greeting")
def chatbot_greeting():
    return jsonify({"reply": chatbot.get_greeting()})


# ---------------------------------------------------------------------------
# API: soil sample photos (field data)
# ---------------------------------------------------------------------------

@app.route("/api/soil-sample/<location_id>", methods=["GET"])
def get_soil_sample(location_id):
    if location_id not in _LOCATIONS_BY_ID:
        return jsonify({"error": f"Unknown location id '{location_id}'"}), 404
    sample = soil_sample.get_sample(location_id)
    if not sample:
        return jsonify({"exists": False})
    return jsonify({"exists": True, **sample})


@app.route("/api/soil-sample/<location_id>", methods=["POST"])
def upload_soil_sample(location_id):
    if location_id not in _LOCATIONS_BY_ID:
        return jsonify({"error": f"Unknown location id '{location_id}'"}), 404

    if "photo" not in request.files:
        return jsonify({"error": "No 'photo' file in the request"}), 400

    photo = request.files["photo"]
    if not photo.filename:
        return jsonify({"error": "Empty filename"}), 400

    ext = "." + photo.filename.rsplit(".", 1)[-1].lower() if "." in photo.filename else ""
    if ext not in soil_sample.ALLOWED_EXTENSIONS:
        return jsonify({"error": "Unsupported file type. Use JPG, PNG or WEBP."}), 400

    try:
        meta = soil_sample.save_sample(location_id, photo)
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the UI
        return jsonify({"error": f"Could not process image: {exc}"}), 400

    meta["image_url"] = f"/api/soil-sample/{location_id}/image"
    return jsonify({"exists": True, **meta})


@app.route("/api/soil-sample/<location_id>/image")
def get_soil_sample_image(location_id):
    path = soil_sample.get_image_path(location_id)
    if not path:
        return jsonify({"error": "No photo uploaded for this location yet"}), 404
    return send_file(path)


# ---------------------------------------------------------------------------
# API: multi-factor field evidence photos
# ---------------------------------------------------------------------------

@app.route("/api/evidence/<location_id>")
def get_evidence(location_id):
    if location_id not in _LOCATIONS_BY_ID:
        return jsonify({"error": f"Unknown location id '{location_id}'"}), 404
    return jsonify({"location_id": location_id, "categories": evidence.CATEGORIES, "items": evidence.list_for(location_id)})


@app.route("/api/evidence/<location_id>/<category>", methods=["POST"])
def upload_evidence(location_id, category):
    if location_id not in _LOCATIONS_BY_ID:
        return jsonify({"error": f"Unknown location id '{location_id}'"}), 404
    if category not in evidence.CATEGORIES:
        return jsonify({"error": "Unsupported evidence category"}), 400
    if "photo" not in request.files:
        return jsonify({"error": "No 'photo' file in the request"}), 400
    photo = request.files["photo"]
    if not photo.filename:
        return jsonify({"error": "Empty filename"}), 400
    try:
        item = evidence.save(location_id, category, photo)
    except Exception as exc:
        return jsonify({"error": f"Could not process image: {exc}"}), 400
    return jsonify({"exists": True, **item})


@app.route("/api/evidence/<location_id>/<category>/image")
def get_evidence_image(location_id, category):
    if location_id not in _LOCATIONS_BY_ID or category not in evidence.CATEGORIES:
        return jsonify({"error": "Unknown location or evidence category"}), 404
    path = evidence.image_path(location_id, category)
    if not path:
        return jsonify({"error": "No evidence photo uploaded for this category yet"}), 404
    return send_file(path)


# ---------------------------------------------------------------------------
# API: health check
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "locations_loaded": len(_LOCATIONS)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
