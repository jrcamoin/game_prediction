import pytest
from pydantic import ValidationError

from app.models import PredictionRequest, Sport, TeamInput
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


def test_team_names_are_normalized_and_must_be_distinct() -> None:
    with pytest.raises(ValidationError, match="must be different"):
        PredictionRequest(
            home_team=TeamInput(name="  Sharks  "),
            away_team=TeamInput(name="sharks"),
        )


def test_blank_team_name_is_rejected() -> None:
    with pytest.raises(ValidationError, match="team name cannot be blank"):
        TeamInput(name="   ")


def test_golf_manual_prediction_is_supported() -> None:
    response = predict_game(
        PredictionRequest(
            sport=Sport.golf,
            home_team=TeamInput(name="Player A", rating=1600, recent_wins=4, recent_losses=1),
            away_team=TeamInput(name="Player B", rating=1500, recent_wins=2, recent_losses=3),
            neutral_site=True,
        )
    )

    assert response.predicted_winner == "Player A"
    assert any(model.name == "Stacked tree model" for model in response.ensemble)


def test_ufc_manual_prediction_is_supported() -> None:
    response = predict_game(
        PredictionRequest(
            sport=Sport.ufc,
            home_team=TeamInput(name="Fighter Red", rating=1580, recent_wins=4, recent_losses=1),
            away_team=TeamInput(name="Fighter Blue", rating=1510, recent_wins=2, recent_losses=3),
            neutral_site=True,
        )
    )

    assert response.predicted_winner == "Fighter Red"
    assert response.home_win_probability > 0.5


def test_expected_value_feature_moves_projection() -> None:
    response = predict_game(
        PredictionRequest(
            sport=Sport.soccer,
            home_team=TeamInput(
                name="Home",
                rating=1500,
                recent_wins=3,
                recent_losses=2,
                expected_value_for=2.0,
                expected_value_against=0.8,
            ),
            away_team=TeamInput(
                name="Away",
                rating=1500,
                recent_wins=3,
                recent_losses=2,
                expected_value_for=0.9,
                expected_value_against=1.6,
            ),
            neutral_site=True,
        )
    )

    assert response.factors.expected_value > 0
    assert response.predicted_winner == "Home"
