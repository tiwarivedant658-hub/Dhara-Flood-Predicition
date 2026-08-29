"""
risk_engine.py
---------------
Turns raw live data (rainfall, soil moisture) + static terrain data
(slope class, historical events) into ONE risk score (0-100) and an alert
band, for a single location.

This is intentionally a transparent, explainable weighted-scoring model
(not a black box) -- for a hackathon judge Q&A you can point at exactly
which factor pushed the score up. docs/API.md documents the exact formula
and docs/DATA_SOURCES.md explains what a production version should upgrade
(e.g. a trained ML model using historical labelled events, satellite soil
moisture, and telemetry from real IoT gauges).

Weights (sum to 100):
  - Rainfall intensity & accumulated forecast : 45
  - Soil moisture (saturation proxy)          : 25
  - Slope stability class (static terrain)    : 20
  - Historical hazard frequency (static)      : 10
"""

from __future__ import annotations

SLOPE_SCORE = {
    "Low": 10,
    "Moderate": 40,
    "High": 70,
    "Very High": 100,
}

ALERT_BANDS = [
    # (min_score, max_score, level, label, color, description)
    (0, 20, "green", "Safe", "#2E7D4F", "Normal conditions. Routine monitoring only."),
    (20, 40, "yellow", "Watch", "#D9A400", "Conditions building. Stay informed, avoid unnecessary travel near streams."),
    (40, 60, "orange", "Warning", "#E07A1F", "Risk rising quickly. Prepare to move, keep go-bag ready, monitor alerts closely."),
    (60, 80, "red", "Danger", "#C13B2E", "High risk. Evacuate low-lying / riverside areas now, avoid stream crossings."),
    (80, 101, "maroon", "Severe", "#7A2020", "Life-threatening. Follow local authority evacuation orders immediately."),
]


def classify(score: float) -> dict:
    for lo, hi, level, label, color, desc in ALERT_BANDS:
        if lo <= score < hi:
            return {"level": level, "label": label, "color": color, "description": desc}
    return {"level": "maroon", "label": "Severe", "color": "#7A2020", "description": ALERT_BANDS[-1][5]}


def _rainfall_score(live: dict) -> float:
    """0-100 sub-score from rainfall intensity + short-term accumulation."""
    intensity = live.get("max_hourly_intensity_mm") or 0.0   # mm in the worst hour
    next6 = live.get("rainfall_next_6h_mm") or 0.0
    next24 = live.get("rainfall_next_24h_mm") or 0.0

    # IMD-style thresholds (approx): >15.6mm/hr is "very heavy" hourly rain.
    intensity_score = min(100, (intensity / 20.0) * 100)
    accum6_score = min(100, (next6 / 60.0) * 100)      # 60mm in 6h is a serious flash-flood trigger
    accum24_score = min(100, (next24 / 150.0) * 100)   # 150mm/24h ~ IMD "extremely heavy"

    return 0.5 * intensity_score + 0.3 * accum6_score + 0.2 * accum24_score


def _soil_score(live: dict) -> float:
    """0-100 sub-score from soil saturation (higher moisture = less
    absorption capacity left = higher runoff risk)."""
    shallow = live.get("soil_moisture_0_7cm")
    mid = live.get("soil_moisture_7_28cm")
    if shallow is None and mid is None:
        return 30.0  # neutral-ish default when data unavailable
    shallow = shallow if shallow is not None else 0.2
    mid = mid if mid is not None else 0.2
    # Open-Meteo soil moisture is m3/m3, realistic range ~0.05 (dry) - 0.5 (saturated)
    avg = (shallow * 0.6) + (mid * 0.4)
    return max(0.0, min(100.0, (avg / 0.45) * 100))


def compute_risk(location: dict, live: dict) -> dict:
    """
    location: one entry from data/locations.json
    live: output of data_fetcher.fetch_live_conditions()
    Returns a dict with the numeric score, its band, and the factor
    breakdown (useful for the "why this score" panel in the UI).
    """
    rainfall_sub = _rainfall_score(live)
    soil_sub = _soil_score(live)
    slope_sub = SLOPE_SCORE.get(location.get("slope_class", "Moderate"), 40)
    history_sub = min(100, (location.get("historical_events", 0) / 13.0) * 100)

    score = (
        0.45 * rainfall_sub +
        0.25 * soil_sub +
        0.20 * slope_sub +
        0.10 * history_sub
    )
    score = round(max(0.0, min(100.0, score)), 1)

    band = classify(score)

    return {
        "score": score,
        **band,
        "factors": {
            "rainfall_subscore": round(rainfall_sub, 1),
            "soil_subscore": round(soil_sub, 1),
            "slope_subscore": round(slope_sub, 1),
            "history_subscore": round(history_sub, 1),
        },
        "live": live,
    }
