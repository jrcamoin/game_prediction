from app.models import PredictionRequest, TeamInput
from app.predictor import predict_game


def test_stronger_home_team_is_favored() -> None:
    response = predict_game(
        PredictionRequest(
            home_team=TeamInput(name="Home", rating=1650, recent_wins=4, recent_losses=1),
            away_team=TeamInput(name="Away", rating=1450, recent_wins=2, recent_losses=3),
        )
    )

    assert response.predicted_winner == "Home"
    assert response.home_win_probability > 0.5


def test_market_odds_can_move_projection() -> None:
    response = predict_game(
        PredictionRequest(
            home_team=TeamInput(name="Home", rating=1500, recent_wins=3, recent_losses=2, moneyline=180),
            away_team=TeamInput(name="Away", rating=1500, recent_wins=3, recent_losses=2, moneyline=-220),
            neutral_site=True,
        )
    )

    assert response.predicted_winner == "Away"
