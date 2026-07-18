from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models import FactorBreakdown


FEATURE_COLUMNS = [
    "rating_edge",
    "advanced_rating_edge",
    "expected_value_edge",
    "recent_form_edge",
    "injury_edge",
    "lineup_edge",
    "rest_edge",
    "venue_edge",
    "travel_edge",
    "market_edge",
    "weather_edge",
]


def trained_probability(factors: FactorBreakdown) -> float | None:
    artifact = _load_artifact()
    if artifact is None:
        return None

    model = artifact.get("model") if isinstance(artifact, dict) else artifact
    features = artifact.get("features", FEATURE_COLUMNS) if isinstance(artifact, dict) else FEATURE_COLUMNS
    values = _feature_values(factors)
    row = [[values[feature] for feature in features]]
    try:
        try:
            import pandas as pd

            payload = pd.DataFrame(row, columns=features)
        except ImportError:
            payload = row
        probability = model.predict_proba(payload)[0][1]
    except (AttributeError, IndexError, TypeError, ValueError):
        return None
    return float(probability)


def trained_artifact_family() -> str | None:
    artifact = _load_artifact()
    if artifact is None:
        return None
    if isinstance(artifact, dict):
        family = artifact.get("family")
        return str(family) if family else "trained-tree"
    return "trained-tree"


@lru_cache(maxsize=1)
def _load_artifact() -> Any | None:
    artifact_path = os.getenv("XGBOOST_MODEL_PATH")
    if not artifact_path or not Path(artifact_path).exists():
        return None
    try:
        import joblib
    except ImportError:
        return None
    try:
        return joblib.load(artifact_path)
    except (OSError, ValueError):
        return None


def _feature_values(factors: FactorBreakdown) -> dict[str, float]:
    return {
        "rating_edge": factors.rating,
        "advanced_rating_edge": factors.advanced_rating,
        "expected_value_edge": factors.expected_value,
        "recent_form_edge": factors.recent_form,
        "injury_edge": factors.injuries,
        "lineup_edge": factors.lineup,
        "rest_edge": factors.rest,
        "venue_edge": factors.venue,
        "travel_edge": factors.travel,
        "market_edge": factors.market,
        "weather_edge": factors.weather,
    }
