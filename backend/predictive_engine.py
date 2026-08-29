"""Predictive flash-flood engine for the DHARA prototype.

This module intentionally separates *prediction* from the old weighted risk score.
It trains a small Random Forest classifier on a physics-informed prototype storm
scenario generator. The model estimates the probability that trigger conditions
will be reached in the next 6 hours.

IMPORTANT: the bundled model is a prototype calibration model, not a claim of
validated operational accuracy. `scripts/train_model.py` is provided so the team
can replace the calibration data with labelled IMD/GSI/MOSDAC/Bhuvan observations.
"""
from __future__ import annotations

from functools import lru_cache
import math
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from pathlib import Path
import joblib

FEATURE_NAMES = [
    "rain_1h", "rain_3h", "rain_6h", "rain_24h", "rain_72h",
    "soil_wetness", "soil_change", "slope_score", "elevation_norm",
    "twi_proxy", "river_proximity", "historical_hazard",
]

MODEL_VERSION = "DHARA-Predictor v2.0 (validated artifact or prototype fallback)"
MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "research" / "dhara_model.joblib"


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def _build_prototype_model() -> RandomForestClassifier:
    """Create a deterministic prototype training set.

    The generator encodes plausible nonlinear interactions: intense rain becomes
    more dangerous when soil is already wet, terrain is steep, drainage is poor,
    and historical hazard frequency is high. This is deliberately labelled as a
    calibration model until real historical event labels are supplied.
    """
    rng = np.random.default_rng(20260828)
    n = 6000
    rain_1h = rng.gamma(1.8, 7.0, n)
    rain_3h = rain_1h + rng.gamma(2.0, 9.0, n)
    rain_6h = rain_3h + rng.gamma(2.2, 12.0, n)
    rain_24h = rain_6h + rng.gamma(2.0, 22.0, n)
    rain_72h = rain_24h + rng.gamma(2.2, 42.0, n)
    soil = np.clip(rng.beta(3.0, 2.0, n), 0.03, 0.98)
    soil_change = np.clip(rng.normal(0.02, 0.10, n), -0.5, 0.5)
    slope = rng.uniform(0, 100, n)
    elevation = rng.uniform(0, 1, n)
    twi = np.clip(rng.normal(0.5, 0.25, n), 0, 1)
    river = np.clip(rng.beta(2.0, 2.0, n), 0, 1)  # 1 = close to drainage
    history = np.clip(rng.beta(2.0, 3.0, n), 0, 1)

    intensity = rain_1h / 25.0
    accumulation = rain_6h / 90.0
    antecedent = rain_72h / 260.0
    saturation = soil * 1.15 + np.maximum(soil_change, 0) * 0.5
    terrain = slope / 100.0
    drainage = 0.6 * twi + 0.4 * river

    latent = (
        3.0 * intensity +
        2.0 * accumulation +
        1.2 * antecedent +
        1.7 * saturation +
        1.2 * terrain +
        1.0 * drainage +
        0.7 * history +
        0.15 * elevation -
        3.0
    )
    p = _sigmoid(latent)
    y = rng.binomial(1, p)

    X = np.column_stack([
        rain_1h, rain_3h, rain_6h, rain_24h, rain_72h,
        soil, soil_change, slope, elevation, twi, river, history,
    ])
    model = RandomForestClassifier(
        n_estimators=100, max_depth=9, min_samples_leaf=5,
        class_weight="balanced", random_state=20260828, n_jobs=1,
    )
    model.fit(X, y)
    return model


@lru_cache(maxsize=1)
def get_model() -> RandomForestClassifier:
    """Load the validated historical model when available; otherwise use the demo fallback."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return _build_prototype_model()


def _norm_slope(location: dict) -> float:
    return {"Low": 0.15, "Moderate": 0.4, "High": 0.7, "Very High": 1.0}.get(location.get("slope_class"), 0.4)


def _feature_vector(location: dict, live: dict) -> np.ndarray:
    shallow = live.get("soil_moisture_0_7cm")
    mid = live.get("soil_moisture_7_28cm")
    soil = ((shallow if shallow is not None else 0.2) * 0.6 + (mid if mid is not None else 0.2) * 0.4) / 0.45
    soil = float(np.clip(soil, 0, 1))
    soil_prev = live.get("soil_moisture_prev")
    soil_change = 0.0 if soil_prev is None else float(np.clip(soil - soil_prev, -0.5, 0.5))
    slope = _norm_slope(location)
    elevation = float(np.clip((location.get("elevation_m", 1000) - 300) / 3300, 0, 1))
    history = float(np.clip((location.get("historical_events", 0) / 13.0), 0, 1))
    # Proxies are explicitly labelled until GIS-derived layers are supplied.
    twi_proxy = float(np.clip(0.25 + 0.55 * slope + 0.20 * history, 0, 1))
    river_proximity = float(np.clip(0.25 + 0.65 * history + 0.10 * (1 - slope), 0, 1))
    return np.array([[
        live.get("rainfall_prev_1h_mm", live.get("rainfall_last_hour_mm", 0.0)),
        live.get("rainfall_last_3h_mm", 0.0),
        live.get("rainfall_last_6h_mm", 0.0) + live.get("rainfall_next_6h_mm", 0.0) * 0.15,
        live.get("rainfall_last_24h_mm", 0.0) + live.get("rainfall_next_24h_mm", 0.0) * 0.10,
        live.get("rainfall_last_72h_mm", 0.0),
        soil, soil_change, slope, elevation, twi_proxy, river_proximity, history,
    ]])


def _estimate_lead_time(live: dict) -> dict:
    forecast = live.get("forecast_hourly_precipitation", []) or []
    if not forecast:
        return {"hours": None, "label": "Unknown"}
    cumulative = 0.0
    for i, mm in enumerate(forecast[:6], start=1):
        cumulative += max(0.0, float(mm or 0))
        if float(mm or 0) >= 20 or cumulative >= 45:
            return {"hours": i, "label": f"~{i}h"}
    return {"hours": 6, "label": ">6h / no trigger yet"}


def predict(location: dict, live: dict) -> dict:
    model = get_model()
    X = _feature_vector(location, live)
    probability = float(model.predict_proba(X)[0, 1])
    probability = round(float(np.clip(probability * 100, 0, 100)), 1)

    # Confidence reflects upstream completeness, not model accuracy.
    expected = [
        live.get("rainfall_last_6h_mm"), live.get("rainfall_last_24h_mm"),
        live.get("rainfall_last_72h_mm"), live.get("rainfall_next_6h_mm"),
        live.get("soil_moisture_0_7cm"), live.get("soil_moisture_7_28cm"),
    ]
    completeness = sum(v is not None for v in expected) / len(expected)
    confidence = round(55 + 40 * completeness, 0)

    # Probability bands are prediction outputs, not the old weighted risk score.
    if probability < 20:
        band = ("green", "Low", "No strong flash-flood trigger is predicted in the next 6 hours.")
    elif probability < 40:
        band = ("yellow", "Watch", "Some trigger conditions are developing; keep monitoring the next forecast updates.")
    elif probability < 60:
        band = ("orange", "Elevated", "The model sees a meaningful chance of trigger conditions within the prediction window.")
    elif probability < 80:
        band = ("red", "High", "The model predicts a high chance of trigger conditions; prepare local response actions.")
    else:
        band = ("maroon", "Severe", "The model predicts severe trigger conditions; follow official evacuation instructions if issued.")

    importances = model.feature_importances_
    names = [
        "Rainfall now", "Rainfall last 3h", "Rainfall 6h window", "Rainfall 24h window", "Rainfall 72h",
        "Soil wetness", "Soil wetness change", "Slope susceptibility", "Elevation", "Drainage proxy",
        "River proximity proxy", "Historical hazard",
    ]
    drivers = sorted(
        [{"name": n, "importance": round(float(v) * 100, 1)} for n, v in zip(names, importances)],
        key=lambda x: x["importance"], reverse=True,
    )[:5]
    lead = _estimate_lead_time(live)
    using_validated_model = MODEL_PATH.exists()
    return {
        "probability": probability,
        "horizon_hours": 6,
        "label": band[1],
        "level": band[0],
        "description": band[2],
        "confidence": confidence,
        "lead_time": lead,
        "model": MODEL_VERSION,
        "model_source": "validated_historical" if using_validated_model else "prototype_synthetic",
        "drivers": drivers,
        "feature_names": FEATURE_NAMES,
        "live": live,
    }
