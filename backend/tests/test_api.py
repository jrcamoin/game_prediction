from fastapi.testclient import TestClient

from app.main import app
from app.trained_model import _load_artifact


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_model_status_lists_new_sports() -> None:
    response = client.get("/api/model/status")

    assert response.status_code == 200
    payload = response.json()
    sports = {capability["sport"]: capability for capability in payload["capabilities"]}
    assert {"soccer", "golf", "ufc"}.issubset(sports)
    assert sports["golf"]["live_schedule"] is True
    assert sports["ufc"]["expected_value"] is True
    assert payload["active_model"] in {"Deterministic stacked tree scaffold", "Trained XGBoost stack"}


def test_manual_ufc_prediction_endpoint() -> None:
    response = client.post(
        "/api/predict",
        json={
            "sport": "ufc",
            "neutral_site": True,
            "home_team": {
                "name": "Fighter Red",
                "rating": 1600,
                "recent_wins": 4,
                "recent_losses": 1,
                "injuries": 0,
                "questionable_players": 0,
                "starters_confirmed": 1,
                "projected_starters": 1,
                "rest_days": 7,
                "moneyline": -140,
            },
            "away_team": {
                "name": "Fighter Blue",
                "rating": 1510,
                "recent_wins": 2,
                "recent_losses": 3,
                "injuries": 1,
                "questionable_players": 0,
                "starters_confirmed": 1,
                "projected_starters": 1,
                "rest_days": 7,
                "moneyline": 120,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["predicted_winner"] == "Fighter Red"
    assert any(model["name"] == "Stacked tree model" for model in payload["ensemble"])


def test_golf_live_prediction_uses_file_backed_provider() -> None:
    games_response = client.get("/api/games/upcoming?sport=golf")
    assert games_response.status_code == 200
    game_id = games_response.json()[0]["id"]

    response = client.post(f"/api/predict/live/golf/{game_id}")

    assert response.status_code == 200
    assert response.json()["game"]["sport"] == "golf"


def test_auth_session_defaults_to_local_mode() -> None:
    response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json()["mode"] == "local"


def test_auth_token_can_issue_and_validate_session(monkeypatch) -> None:
    monkeypatch.setenv("APP_AUTH_TOKEN", "test-secret")

    token_response = client.post("/api/auth/token?subject=tester", headers={"Authorization": "Bearer test-secret"})
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]

    session_response = client.get("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert session_response.status_code == 200
    assert session_response.json()["mode"] == "jwt"
    assert session_response.json()["subject"] == "tester"


def test_model_status_does_not_mark_missing_artifact_loaded(monkeypatch) -> None:
    monkeypatch.setenv("XGBOOST_MODEL_PATH", "missing.joblib")
    _load_artifact.cache_clear()

    response = client.get("/api/model/status")

    assert response.status_code == 200
    assert response.json()["trained_artifact_loaded"] is False
