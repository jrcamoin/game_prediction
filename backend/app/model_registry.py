from __future__ import annotations

import os
from pathlib import Path

from app.data_sources import SCHEDULE_SUPPORTED_SPORTS
from app.models import ModelStatus, Sport, SportCapability
from app.statbomb import statbomb_enabled


LIVE_STATE_SUPPORTED = {Sport.football, Sport.basketball, Sport.baseball, Sport.hockey, Sport.soccer}
EXPECTED_VALUE_SUPPORTED = {Sport.soccer, Sport.golf, Sport.ufc}


def model_status() -> ModelStatus:
    artifact_path = os.getenv("XGBOOST_MODEL_PATH")
    artifact_loaded = bool(artifact_path and Path(artifact_path).exists())
    active_model = "Trained XGBoost stack" if artifact_loaded else "Deterministic stacked tree scaffold"

    return ModelStatus(
        active_model=active_model,
        trained_artifact_path=artifact_path,
        trained_artifact_loaded=artifact_loaded,
        capabilities=[_sport_capability(sport, artifact_loaded) for sport in Sport],
    )


def _sport_capability(sport: Sport, artifact_loaded: bool) -> SportCapability:
    notes: list[str] = []
    if sport in {Sport.golf, Sport.ufc}:
        notes.append("File-backed schedule provider is active; set sport-specific JSON env vars for real feeds.")
    if sport == Sport.soccer and not statbomb_enabled():
        notes.append("StatsBomb xG enrichment is optional and not currently configured.")
    if not artifact_loaded:
        notes.append("Using deterministic stacked tree scaffold until a trained model artifact is configured.")

    return SportCapability(
        sport=sport,
        live_schedule=sport in SCHEDULE_SUPPORTED_SPORTS,
        live_state=sport in LIVE_STATE_SUPPORTED,
        odds=sport in SCHEDULE_SUPPORTED_SPORTS,
        expected_value=sport in EXPECTED_VALUE_SUPPORTED,
        trained_model=artifact_loaded,
        model_name="XGBoost stack" if artifact_loaded else "Stacked tree scaffold",
        notes=notes,
    )
