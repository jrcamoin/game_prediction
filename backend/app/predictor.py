from math import exp

from app.models import FactorBreakdown, PredictionRequest, PredictionResponse, Sport, TeamInput


HOME_FIELD_BY_SPORT: dict[Sport, float] = {
    Sport.football: 55.0,
    Sport.basketball: 45.0,
    Sport.baseball: 30.0,
    Sport.hockey: 35.0,
    Sport.soccer: 50.0,
}


def predict_game(request: PredictionRequest) -> PredictionResponse:
    factors = FactorBreakdown(
        rating=(request.home_team.rating - request.away_team.rating) * 0.018,
        recent_form=_recent_form_edge(request.home_team, request.away_team),
        injuries=(request.away_team.injuries - request.home_team.injuries) * 0.18,
        rest=(request.home_team.rest_days - request.away_team.rest_days) * 0.08,
        venue=0 if request.neutral_site else HOME_FIELD_BY_SPORT[request.sport] * 0.018,
        travel=(request.away_travel_miles - request.home_travel_miles) / 1000 * 0.08,
        market=_market_edge(request.home_team.moneyline, request.away_team.moneyline),
    )
    score = sum(factors.model_dump().values())
    home_probability = _sigmoid(score)
    away_probability = 1 - home_probability
    predicted_winner = request.home_team.name if home_probability >= 0.5 else request.away_team.name

    return PredictionResponse(
        predicted_winner=predicted_winner,
        home_win_probability=round(home_probability, 4),
        away_win_probability=round(away_probability, 4),
        confidence=_confidence(abs(home_probability - 0.5)),
        score=round(score, 4),
        factors=factors,
        summary=_summary(request, home_probability, predicted_winner),
    )


def _recent_form_edge(home_team: TeamInput, away_team: TeamInput) -> float:
    home_games = home_team.recent_wins + home_team.recent_losses
    away_games = away_team.recent_wins + away_team.recent_losses
    home_pct = home_team.recent_wins / home_games
    away_pct = away_team.recent_wins / away_games
    return (home_pct - away_pct) * 0.75


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
    return f"{predicted_winner} is projected to win with {probability:.1%} probability."
