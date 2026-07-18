from math import exp

from app.models import FactorBreakdown, FeatureImportance, ModelPrediction, PredictionRequest, PredictionResponse, Sport, TeamInput
from app.trained_model import trained_probability


HOME_FIELD_BY_SPORT: dict[Sport, float] = {
    Sport.football: 55.0,
    Sport.basketball: 45.0,
    Sport.baseball: 30.0,
    Sport.hockey: 35.0,
    Sport.soccer: 50.0,
    Sport.golf: 0.0,
    Sport.ufc: 0.0,
}


def predict_game(request: PredictionRequest) -> PredictionResponse:
    factors = _factor_breakdown(request)
    score = sum(factors.model_dump().values())
    model_predictions = _ensemble_predictions(request, factors)
    home_probability = _weighted_probability(model_predictions)
    calibrated_home_probability = _calibrate_probability(home_probability)
    away_probability = 1 - home_probability
    predicted_winner = request.home_team.name if home_probability >= 0.5 else request.away_team.name

    return PredictionResponse(
        predicted_winner=predicted_winner,
        home_win_probability=round(home_probability, 4),
        away_win_probability=round(away_probability, 4),
        calibrated_home_win_probability=round(calibrated_home_probability, 4),
        confidence=_confidence(abs(calibrated_home_probability - 0.5)),
        score=round(score, 4),
        factors=factors,
        ensemble=model_predictions,
        feature_importance=_feature_importance(factors),
        model_notes=_model_notes(request),
        summary=_summary(request, calibrated_home_probability, predicted_winner),
    )


def _factor_breakdown(request: PredictionRequest) -> FactorBreakdown:
    return FactorBreakdown(
        rating=(request.home_team.rating - request.away_team.rating) * 0.018,
        advanced_rating=(request.home_team.rating - request.away_team.rating) * 0.008,
        expected_value=_expected_value_edge(request.home_team, request.away_team),
        recent_form=_recent_form_edge(request.home_team, request.away_team),
        injuries=(request.away_team.injuries - request.home_team.injuries) * 0.18
        + (request.away_team.questionable_players - request.home_team.questionable_players) * 0.06,
        lineup=_lineup_edge(request.home_team, request.away_team),
        rest=(request.home_team.rest_days - request.away_team.rest_days) * 0.08,
        venue=0 if request.neutral_site else HOME_FIELD_BY_SPORT[request.sport] * 0.018,
        travel=(request.away_travel_miles - request.home_travel_miles) / 1000 * 0.08,
        market=_market_edge(request.home_team.moneyline, request.away_team.moneyline),
        weather=_weather_edge(request),
    )


def _ensemble_predictions(request: PredictionRequest, factors: FactorBreakdown) -> list[ModelPrediction]:
    rating_form_score = factors.rating + factors.advanced_rating + factors.expected_value * 0.65 + factors.recent_form + factors.venue
    market_score = factors.market + factors.rating * 0.35 + factors.expected_value * 0.2 + factors.venue * 0.3
    availability_score = (
        factors.injuries
        + factors.lineup
        + factors.rest
        + factors.travel
        + factors.weather
        + factors.expected_value * 0.3
        + factors.rating * 0.25
    )
    tree_score = _stacked_tree_score(request, factors)
    trained_tree_probability = trained_probability(factors)
    market_weight = 0.28 if request.home_team.moneyline is not None and request.away_team.moneyline is not None else 0.12
    tree_weight = 0.22
    rating_weight = 0.38 if market_weight < 0.2 else 0.32
    availability_weight = 1 - rating_weight - market_weight - tree_weight

    return [
        ModelPrediction(name="Rating + form", home_win_probability=round(_sigmoid(rating_form_score), 4), weight=round(rating_weight, 2)),
        ModelPrediction(name="Market-aware", home_win_probability=round(_sigmoid(market_score), 4), weight=round(market_weight, 2)),
        ModelPrediction(name="Availability + context", home_win_probability=round(_sigmoid(availability_score), 4), weight=round(availability_weight, 2)),
        ModelPrediction(
            name="Trained XGBoost stack" if trained_tree_probability is not None else "Stacked tree model",
            home_win_probability=round(trained_tree_probability if trained_tree_probability is not None else _sigmoid(tree_score), 4),
            weight=round(tree_weight, 2),
        ),
    ]


def _weighted_probability(predictions: list[ModelPrediction]) -> float:
    total_weight = sum(prediction.weight for prediction in predictions)
    if total_weight == 0:
        return 0.5
    return sum(prediction.home_win_probability * prediction.weight for prediction in predictions) / total_weight


def _calibrate_probability(probability: float) -> float:
    # Shrink extreme outputs toward 50% until the model is calibrated on historical holdout data.
    return 0.5 + (probability - 0.5) * 0.88


def _recent_form_edge(home_team: TeamInput, away_team: TeamInput) -> float:
    home_games = home_team.recent_wins + home_team.recent_losses
    away_games = away_team.recent_wins + away_team.recent_losses
    home_pct = home_team.recent_wins / home_games
    away_pct = away_team.recent_wins / away_games
    return (home_pct - away_pct) * 0.75


def _lineup_edge(home_team: TeamInput, away_team: TeamInput) -> float:
    home_rate = home_team.starters_confirmed / max(home_team.projected_starters, 1)
    away_rate = away_team.starters_confirmed / max(away_team.projected_starters, 1)
    return (home_rate - away_rate) * 0.22


def _expected_value_edge(home_team: TeamInput, away_team: TeamInput) -> float:
    if (
        home_team.expected_value_for is None
        or home_team.expected_value_against is None
        or away_team.expected_value_for is None
        or away_team.expected_value_against is None
    ):
        return 0

    home_net = home_team.expected_value_for - home_team.expected_value_against
    away_net = away_team.expected_value_for - away_team.expected_value_against
    return max(-1.2, min(1.2, (home_net - away_net) * 0.42))


def _stacked_tree_score(request: PredictionRequest, factors: FactorBreakdown) -> float:
    """Deterministic tree stack placeholder for a future trained XGBoost artifact."""
    tree_outputs = [
        _tree_rating_context(factors),
        _tree_market_availability(request, factors),
        _tree_sport_specific(request, factors),
    ]
    return sum(tree_outputs) / len(tree_outputs)


def _tree_rating_context(factors: FactorBreakdown) -> float:
    score = 0.0
    if factors.rating > 1.8:
        score += 0.95
    elif factors.rating > 0.45:
        score += 0.35
    elif factors.rating < -1.8:
        score -= 0.95
    elif factors.rating < -0.45:
        score -= 0.35

    if factors.recent_form > 0.25:
        score += 0.18
    elif factors.recent_form < -0.25:
        score -= 0.18
    return score + factors.venue * 0.25


def _tree_market_availability(request: PredictionRequest, factors: FactorBreakdown) -> float:
    score = factors.market * 0.85 + factors.injuries * 0.45 + factors.lineup * 0.35
    if request.home_team.moneyline is None or request.away_team.moneyline is None:
        score += factors.rating * 0.18
    if abs(factors.market) > 0.4 and factors.market * factors.rating < 0:
        score *= 0.72
    return score


def _tree_sport_specific(request: PredictionRequest, factors: FactorBreakdown) -> float:
    score = factors.expected_value * 0.9 + factors.rest * 0.25 + factors.travel * 0.18 + factors.weather * 0.4
    if request.sport == Sport.ufc:
        score += factors.injuries * 0.3
    if request.sport == Sport.golf:
        score += factors.advanced_rating * 0.55
    if request.sport == Sport.soccer and abs(factors.expected_value) > 0.35:
        score += factors.expected_value * 0.35
    return score


def _weather_edge(request: PredictionRequest) -> float:
    if request.weather is None or request.sport not in {Sport.football, Sport.baseball, Sport.soccer}:
        return 0

    penalty = 0.0
    if request.weather.wind_mph and request.weather.wind_mph >= 18:
        penalty -= 0.04
    if request.weather.wind_gust_mph and request.weather.wind_gust_mph >= 28:
        penalty -= 0.03
    if request.weather.precipitation_probability and request.weather.precipitation_probability >= 45:
        penalty -= 0.03
    if request.weather.temperature_f is not None and (request.weather.temperature_f <= 35 or request.weather.temperature_f >= 92):
        penalty -= 0.02
    return penalty if not request.neutral_site else penalty * 0.5


def _market_edge(home_moneyline: int | None, away_moneyline: int | None) -> float:
    if home_moneyline is None or away_moneyline is None:
        return 0

    home_implied = _american_odds_to_probability(home_moneyline)
    away_implied = _american_odds_to_probability(away_moneyline)
    total = home_implied + away_implied
    if total == 0:
        return 0

    no_vig_home_probability = home_implied / total
    return (no_vig_home_probability - 0.5) * 1.6


def _american_odds_to_probability(odds: int) -> float:
    if odds == 0:
        return 0.5
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)


def _sigmoid(score: float) -> float:
    return 1 / (1 + exp(-score))


def _confidence(distance_from_coinflip: float) -> str:
    if distance_from_coinflip >= 0.24:
        return "high"
    if distance_from_coinflip >= 0.12:
        return "medium"
    return "low"


def _summary(request: PredictionRequest, home_probability: float, predicted_winner: str) -> str:
    probability = home_probability if predicted_winner == request.home_team.name else 1 - home_probability
    return f"{predicted_winner} is projected to win with {probability:.1%} calibrated probability."


def _feature_importance(factors: FactorBreakdown) -> list[FeatureImportance]:
    items = []
    for name, value in factors.model_dump().items():
        items.append(
            FeatureImportance(
                name=name,
                value=round(value, 4),
                impact=round(abs(value), 4),
                direction="home" if value > 0 else "away" if value < 0 else "neutral",
            )
        )
    return sorted(items, key=lambda item: item.impact, reverse=True)


def _model_notes(request: PredictionRequest) -> list[str]:
    notes = [
        "Probabilities are calibrated by shrinking ensemble outputs toward 50% until historical calibration is added.",
    ]
    if trained_probability(_factor_breakdown(request)) is None:
        notes.append("Stacked tree model is a deterministic boosted-tree scaffold; set XGBOOST_MODEL_PATH to use a trained artifact.")
    else:
        notes.append("Trained XGBoost artifact is active in the ensemble.")
    if request.home_team.expected_value_for is not None and request.away_team.expected_value_for is not None:
        notes.append("Sport-specific expected-value data is included in the ensemble.")
    if request.weather is not None:
        notes.append(f"Weather included: {request.weather.summary}")
    if request.home_team.starters_confirmed == 0 and request.away_team.starters_confirmed == 0:
        notes.append("Lineup detection is using defaults because confirmed starters were not supplied.")
    if request.home_team.moneyline is None or request.away_team.moneyline is None:
        notes.append("Market model weight is reduced because moneyline odds are unavailable.")
    return notes
