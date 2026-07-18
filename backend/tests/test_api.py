from fastapi.testclient import TestClient

from app.main import app


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
