"""
soil_sample.py
---------------
Lets a field volunteer attach a PHOTO of the actual soil at a settlement,
alongside the live Open-Meteo soil-moisture number already shown in the
detail drawer. This is the "boots on the ground" data point the modelled
data can't give you.

IMPORTANT HONESTY NOTE (read before demoing this to judges):
The "analysis" here is a simple, transparent visual heuristic - it looks at
the average brightness/tone of the photo and buckets it into a qualitative
label ("looks dark & likely moist" / "looks pale & likely dry" etc). It is
NOT a calibrated soil-moisture sensor and should never be presented as one.
It exists to (a) give the field photo *some* immediate on-screen value, and
(b) as a clearly-labelled placeholder for where a real trained image
classifier (e.g. a small CNN fine-tuned on labelled soil-moisture photos)
would plug in later - see the "upgrade path" note at the bottom of this file.

Storage: one photo per location, saved to data/soil_samples/<location_id>/.
Simple by design for a hackathon prototype - swap for a DB + object storage
(S3/GCS) if you need history of multiple samples per location.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "data" / "soil_samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_BYTES = 8 * 1024 * 1024  # 8 MB


def _location_dir(location_id: str) -> Path:
    d = SAMPLES_DIR / location_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _meta_path(location_id: str) -> Path:
    return _location_dir(location_id) / "meta.json"


def _image_path(location_id: str) -> Path | None:
    d = _location_dir(location_id)
    for ext in ALLOWED_EXTENSIONS:
        p = d / f"sample{ext}"
        if p.exists():
            return p
    return None


def analyze_image(path: Path) -> dict:
    """Cheap, transparent visual heuristic -- see module docstring."""
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((160, 160))  # small enough to average fast
        pixels = list(img.getdata())

    n = len(pixels)
    avg_r = sum(p[0] for p in pixels) / n
    avg_g = sum(p[1] for p in pixels) / n
    avg_b = sum(p[2] for p in pixels) / n
    brightness = (avg_r + avg_g + avg_b) / 3.0  # 0 (black) - 255 (white)

    if brightness < 90:
        moisture_label = "Looks dark - visually consistent with moist/saturated soil"
        moisture_hint = "dark"
    elif brightness < 160:
        moisture_label = "Looks moderately toned - visually consistent with slightly moist soil"
        moisture_hint = "moderate"
    else:
        moisture_label = "Looks pale/light - visually consistent with dry soil"
        moisture_hint = "dry"

    # Rough reddish/brown vs grey tone (very approximate, just for a bit of colour)
    reddish = avg_r - ((avg_g + avg_b) / 2)
    tone = "reddish-brown tone" if reddish > 12 else "grey/neutral tone"

    return {
        "avg_brightness": round(brightness, 1),
        "avg_rgb": [round(avg_r, 1), round(avg_g, 1), round(avg_b, 1)],
        "moisture_hint": moisture_hint,
        "label": moisture_label,
        "tone_note": tone,
    }


def save_sample(location_id: str, file_storage) -> dict:
    """
    file_storage: a Werkzeug FileStorage object from request.files['photo']
    Overwrites any previous sample for this location (single "latest" photo
    per location, by design - see module docstring for how to extend to
    keep history).
    """
    filename = (file_storage.filename or "").lower()
    ext = Path(filename).suffix or ".jpg"
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".jpg"

    # Clear any previous sample (any extension) so we never accumulate stale files.
    d = _location_dir(location_id)
    for old in d.glob("sample.*"):
        old.unlink(missing_ok=True)

    dest = d / f"sample{ext}"
    file_storage.save(dest)

    analysis = analyze_image(dest)
    meta = {
        "location_id": location_id,
        "filename": dest.name,
        "uploaded_at": int(time.time()),
        "analysis": analysis,
    }
    _meta_path(location_id).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def get_sample(location_id: str) -> dict | None:
    meta_path = _meta_path(location_id)
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    img = _image_path(location_id)
    if not img:
        return None
    meta["image_url"] = f"/api/soil-sample/{location_id}/image"
    return meta


def get_image_path(location_id: str) -> Path | None:
    return _image_path(location_id)


# ---------------------------------------------------------------------------
# Upgrade path: to replace this heuristic with a real trained model later,
# swap the body of analyze_image() for a call to your model, e.g.:
#
#   prediction = soil_model.predict(path)   # returns a calibrated % moisture
#
# and keep returning a dict with the same keys (or extend it) so the
# frontend / API contract in app.py doesn't need to change.
# ---------------------------------------------------------------------------
