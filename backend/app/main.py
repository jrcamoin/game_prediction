import random
import csv
import io
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from app.auth import auth_enabled, require_session
from app.data_sources import build_prediction_request_from_game, game_to_prediction_request, list_upcoming_games, resolve_game_result
from app.models import (
    CommunityDashboard,
    Contest,
    ContestCreate,
    ContestEntry,
    ContestEntryCreate,
    DailyFeed,
    Favorite,
    FavoriteCreate,
    Follow,
    FollowCreate,
    GameResult,
    GameComment,
    GameCommentCreate,
    GameSnapshot,
    LivePredictionResponse,
    LiveGameState,
    LeaderboardEntry,
    BettingValuePick,
    NotificationPreferences,
    ModelPerformanceReport,
    ModelStatus,
    Plan,
    PremiumAnalysis,
    PremiumFeatureSet,
    PredictionRequest,
    PredictionResponse,
    PredictionSummary,
    PublicProfile,
    RecommendedPick,
    SavedPrediction,
    SeasonSimulation,
    SimulatedTeamSeason,
    Sport,
    UserProfile,
    UserProfileCreate,
    WeeklyChallenge,
)
from app.live import get_live_game_state
from app.model_registry import model_status
from app.predictor import predict_game
from app.storage import (
    add_favorite,
    add_contest_entry,
    add_game_comment,
    community_dashboard,
    create_user_profile,
    create_contest,
    delete_favorite,
    follow_user,
    get_user_profile,
    get_public_profile,
    init_db,
    leaderboard,
    list_contest_entries,
    list_contests,
    list_favorites,
    list_following,
    list_game_comments,
    list_predictions,
    list_public_profiles,
    list_user_profiles,
    mark_prediction_resolved,
    model_performance_report,
    prediction_export_rows,
    prediction_summary,
    save_live_prediction,
    unfollow_user,
    unresolved_predictions,
    update_notification_preferences,
    update_user_plan,
    weekly_challenges,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="Sports Game Winner Predictor API",
    version="0.1.0",
    description="Transparent baseline API for predicting sports game winners.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/session")
def auth_session(session: dict[str, str] = Depends(require_session)) -> dict[str, str | bool]:
    return {
        "authenticated": True,
        "auth_required": auth_enabled(),
        **session,
    }


@app.get("/api/model/status", response_model=ModelStatus)
def model_capabilities() -> ModelStatus:
    return model_status()


@app.post("/api/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    return predict_game(request)


@app.post("/api/predict/batch", response_model=list[PredictionResponse])
def predict_batch(requests: list[PredictionRequest]) -> list[PredictionResponse]:
    return [predict_game(request) for request in requests]


@app.get("/api/games/upcoming", response_model=list[GameSnapshot])
def upcoming_games(sport: Sport = Sport.basketball, days: int = 14) -> list[GameSnapshot]:
    bounded_days = min(max(days, 1), 30)
    return list_upcoming_games(sport, days=bounded_days)


@app.get("/api/games/recommendations", response_model=list[RecommendedPick])
def recommended_picks(sport: Sport = Sport.basketball, days: int = 14, limit: int = 5) -> list[RecommendedPick]:
    bounded_days = min(max(days, 1), 30)
    bounded_limit = min(max(limit, 1), 20)
    picks: list[RecommendedPick] = []

    for game in list_upcoming_games(sport, days=bounded_days):
        prediction = predict_game(game_to_prediction_request(game))
        probability = (
            prediction.calibrated_home_win_probability
            if prediction.predicted_winner == game.home_team.name
            else 1 - prediction.calibrated_home_win_probability
        )
        picks.append(
            RecommendedPick(
                game_id=game.id,
                sport=game.sport,
                game_date=game.date,
                game_name=game.name,
                predicted_winner=prediction.predicted_winner,
                probability=probability,
                confidence=prediction.confidence,
                home_team=game.home_team.name,
                away_team=game.away_team.name,
            )
        )

    return sorted(picks, key=lambda pick: pick.probability, reverse=True)[:bounded_limit]


@app.get("/api/simulations/season", response_model=SeasonSimulation)
def simulate_season(sport: Sport = Sport.baseball, days: int = 30, simulations: int = 1000) -> SeasonSimulation:
    bounded_days = min(max(days, 1), 30)
    bounded_simulations = min(max(simulations, 100), 5000)
    games = list_upcoming_games(sport, days=bounded_days)
    expected_wins: dict[str, float] = {}
    simulated_wins: dict[str, list[int]] = {}

    probabilities = []
    for game in games:
        prediction = predict_game(game_to_prediction_request(game))
        home_probability = prediction.calibrated_home_win_probability
        probabilities.append((game.home_team.name, game.away_team.name, home_probability))
        expected_wins[game.home_team.name] = expected_wins.get(game.home_team.name, 0) + home_probability
        expected_wins[game.away_team.name] = expected_wins.get(game.away_team.name, 0) + (1 - home_probability)
        simulated_wins.setdefault(game.home_team.name, [])
        simulated_wins.setdefault(game.away_team.name, [])

    rng = random.Random(42)
    totals: dict[str, list[int]] = {team: [] for team in simulated_wins}
    for _ in range(bounded_simulations):
        season_total = {team: 0 for team in simulated_wins}
        for home_team, away_team, home_probability in probabilities:
            if rng.random() < home_probability:
                season_total[home_team] += 1
            else:
                season_total[away_team] += 1
        for team, wins in season_total.items():
            totals[team].append(wins)

    ranked = sorted(expected_wins, key=expected_wins.get, reverse=True)
    teams = [
        SimulatedTeamSeason(
            team=team,
            expected_wins=round(expected_wins[team], 2),
            simulated_wins=round(sum(totals[team]) / max(len(totals[team]), 1)),
            playoff_seed=index + 1,
        )
        for index, team in enumerate(ranked)
    ]
    return SeasonSimulation(sport=sport, simulations=bounded_simulations, remaining_games=len(games), teams=teams)


@app.post("/api/predict/live/{sport}/{game_id}", response_model=LivePredictionResponse)
def predict_live_game(sport: Sport, game_id: str) -> LivePredictionResponse:
    try:
        game = build_prediction_request_from_game(sport, game_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    prediction = predict_game(game_to_prediction_request(game))
    save_live_prediction(game, prediction)
    return LivePredictionResponse(**prediction.model_dump(), game=game)


@app.get("/api/predictions", response_model=list[SavedPrediction])
def saved_predictions(limit: int = 25, query: str | None = None, sport: Sport | None = None) -> list[SavedPrediction]:
    return list_predictions(limit=limit, query=query, sport=sport)


@app.get("/api/predictions/summary", response_model=PredictionSummary)
def saved_prediction_summary() -> PredictionSummary:
    return prediction_summary()


@app.post("/api/predictions/grade", response_model=list[SavedPrediction])
def grade_saved_predictions() -> list[SavedPrediction]:
    graded: list[SavedPrediction] = []
    for prediction in unresolved_predictions():
        result = resolve_game_result(prediction.sport, prediction.game_id)
        if result is None or not result.completed:
            continue
        resolved = mark_prediction_resolved(prediction.id, result)
        if resolved is not None:
            graded.append(resolved)
    return graded


@app.get("/api/games/result/{sport}/{game_id}", response_model=GameResult)
def game_result(sport: Sport, game_id: str) -> GameResult:
    result = resolve_game_result(sport, game_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Game result was not found")
    return result


@app.get("/api/live/{sport}/{game_id}", response_model=LiveGameState)
def live_game_state(sport: Sport, game_id: str) -> LiveGameState:
    if sport in {Sport.golf, Sport.ufc}:
        raise HTTPException(status_code=404, detail=f"Live game state is not configured for {sport.value}.")
    return get_live_game_state(sport, game_id)


@app.get("/api/users", response_model=list[UserProfile])
def users() -> list[UserProfile]:
    return list_user_profiles()


@app.post("/api/users", response_model=UserProfile)
def create_user(profile: UserProfileCreate) -> UserProfile:
    return create_user_profile(profile)


@app.get("/api/users/{user_id}", response_model=UserProfile)
def user_profile(user_id: int) -> UserProfile:
    profile = get_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile was not found")
    return profile


@app.put("/api/users/{user_id}/notifications", response_model=UserProfile)
def update_notifications(user_id: int, preferences: NotificationPreferences) -> UserProfile:
    profile = update_notification_preferences(user_id, preferences)
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile was not found")
    return profile


@app.get("/api/users/{user_id}/favorites", response_model=list[Favorite])
def user_favorites(user_id: int) -> list[Favorite]:
    if get_user_profile(user_id) is None:
        raise HTTPException(status_code=404, detail="User profile was not found")
    return list_favorites(user_id)


@app.post("/api/users/{user_id}/favorites", response_model=Favorite)
def create_favorite(user_id: int, favorite: FavoriteCreate) -> Favorite:
    if get_user_profile(user_id) is None:
        raise HTTPException(status_code=404, detail="User profile was not found")
    return add_favorite(user_id, favorite)


@app.delete("/api/users/{user_id}/favorites/{favorite_id}", status_code=204)
def remove_favorite(user_id: int, favorite_id: int) -> None:
    delete_favorite(user_id, favorite_id)


@app.get("/api/users/{user_id}/daily-feed", response_model=DailyFeed)
def daily_feed(user_id: int, limit: int = 8) -> DailyFeed:
    profile = get_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile was not found")

    favorites = list_favorites(user_id)
    favorite_sports = list(dict.fromkeys(favorite.sport for favorite in favorites)) or [Sport.baseball, Sport.basketball, Sport.football]
    favorite_team_names = {
        favorite.team_name.casefold()
        for favorite in favorites
        if favorite.team_name
    }
    picks: list[RecommendedPick] = []

    for sport in favorite_sports:
        sport_picks = recommended_picks(sport=sport, days=30, limit=20)
        for pick in sport_picks:
            team_match = (
                pick.home_team.casefold() in favorite_team_names
                or pick.away_team.casefold() in favorite_team_names
                or pick.predicted_winner.casefold() in favorite_team_names
            )
            if not favorite_team_names or team_match:
                picks.append(pick)

    if len(picks) < limit:
        for sport in favorite_sports:
            picks.extend(recommended_picks(sport=sport, days=30, limit=limit))

    unique: dict[str, RecommendedPick] = {}
    for pick in sorted(picks, key=lambda item: item.probability, reverse=True):
        unique.setdefault(f"{pick.sport}:{pick.game_id}", pick)

    return DailyFeed(
        profile=profile,
        favorites=favorites,
        picks=list(unique.values())[: min(max(limit, 1), 20)],
    )


@app.get("/api/community", response_model=CommunityDashboard)
def community(user_id: int | None = None) -> CommunityDashboard:
    return community_dashboard(user_id)


@app.get("/api/community/profiles", response_model=list[PublicProfile])
def public_profiles() -> list[PublicProfile]:
    return list_public_profiles()


@app.get("/api/community/profiles/{user_id}", response_model=PublicProfile)
def public_profile(user_id: int) -> PublicProfile:
    profile = get_public_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Public profile was not found")
    return profile


@app.post("/api/community/follows", response_model=Follow)
def follow(follow: FollowCreate) -> Follow:
    if get_user_profile(follow.follower_id) is None or get_user_profile(follow.following_id) is None:
        raise HTTPException(status_code=404, detail="User profile was not found")
    try:
        return follow_user(follow)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/community/follows/{follower_id}/{following_id}", status_code=204)
def unfollow(follower_id: int, following_id: int) -> None:
    unfollow_user(follower_id, following_id)


@app.get("/api/community/following/{user_id}", response_model=list[PublicProfile])
def following(user_id: int) -> list[PublicProfile]:
    return list_following(user_id)


@app.get("/api/community/comments/{sport}/{game_id}", response_model=list[GameComment])
def game_comments(sport: Sport, game_id: str) -> list[GameComment]:
    return list_game_comments(sport, game_id)


@app.post("/api/community/comments", response_model=GameComment)
def create_comment(comment: GameCommentCreate) -> GameComment:
    if get_user_profile(comment.user_id) is None:
        raise HTTPException(status_code=404, detail="User profile was not found")
    return add_game_comment(comment)


@app.get("/api/community/contests", response_model=list[Contest])
def contests() -> list[Contest]:
    return list_contests()


@app.post("/api/community/contests", response_model=Contest)
def create_prediction_contest(contest: ContestCreate) -> Contest:
    return create_contest(contest)


@app.get("/api/community/contests/{contest_id}/entries", response_model=list[ContestEntry])
def contest_entries(contest_id: int) -> list[ContestEntry]:
    return list_contest_entries(contest_id)


@app.post("/api/community/contests/{contest_id}/entries", response_model=ContestEntry)
def create_contest_prediction_entry(contest_id: int, entry: ContestEntryCreate) -> ContestEntry:
    if get_user_profile(entry.user_id) is None:
        raise HTTPException(status_code=404, detail="User profile was not found")
    return add_contest_entry(contest_id, entry)


@app.get("/api/community/leaderboard", response_model=list[LeaderboardEntry])
def community_leaderboard(limit: int = 25) -> list[LeaderboardEntry]:
    return leaderboard(limit)


@app.get("/api/community/challenges", response_model=list[WeeklyChallenge])
def challenges(user_id: int | None = None) -> list[WeeklyChallenge]:
    return weekly_challenges(user_id)


@app.get("/api/premium/features/{user_id}", response_model=PremiumFeatureSet)
def premium_features(user_id: int) -> PremiumFeatureSet:
    profile = get_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile was not found")
    return _premium_feature_set(profile.plan)


@app.post("/api/premium/upgrade/{user_id}", response_model=UserProfile)
def upgrade_to_pro(user_id: int) -> UserProfile:
    profile = update_user_plan(user_id, Plan.pro)
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile was not found")
    return profile


@app.get("/api/premium/performance", response_model=ModelPerformanceReport)
def premium_model_performance(user_id: int) -> ModelPerformanceReport:
    _require_pro(user_id)
    return model_performance_report()


@app.get("/api/premium/value-picks", response_model=list[BettingValuePick])
def premium_value_picks(user_id: int, sport: Sport = Sport.baseball, days: int = 14) -> list[BettingValuePick]:
    _require_pro(user_id)
    return _value_picks(sport, days)


@app.get("/api/premium/analysis/{sport}/{game_id}", response_model=PremiumAnalysis)
def premium_analysis(user_id: int, sport: Sport, game_id: str) -> PremiumAnalysis:
    _require_pro(user_id)
    try:
        game = build_prediction_request_from_game(sport, game_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    prediction = predict_game(game_to_prediction_request(game))
    value_pick = _value_pick_for_game(game, prediction)
    top_risks = [
        item.name.replace("_", " ")
        for item in prediction.feature_importance
        if item.direction != ("home" if prediction.predicted_winner == game.home_team.name else "away")
    ][:3]
    return PremiumAnalysis(
        game_id=game.id,
        sport=sport,
        headline=f"{prediction.predicted_winner} is the premium model side at {max(prediction.calibrated_home_win_probability, 1 - prediction.calibrated_home_win_probability):.1%}.",
        model_edge_summary="Premium analysis combines calibrated ensemble output, feature importance, market availability, weather, and lineup context.",
        risk_factors=top_risks or ["No major opposing factors detected."],
        suggested_watch_points=prediction.model_notes + [f"Top driver: {prediction.feature_importance[0].name.replace('_', ' ') if prediction.feature_importance else 'model consensus'}."],
        value_pick=value_pick,
        disclaimer="Analytics only. This is not financial advice or a recommendation to place a bet. Follow applicable laws in your jurisdiction.",
    )


@app.get("/api/premium/export/predictions.csv")
def premium_predictions_csv(user_id: int) -> Response:
    _require_pro(user_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "created_at", "sport", "game", "predicted_winner", "confidence", "home_probability", "away_probability", "actual_winner", "correct"])
    for item in prediction_export_rows():
        writer.writerow([
            item.id,
            item.created_at,
            item.sport.value,
            item.game_name,
            item.predicted_winner,
            item.confidence,
            item.home_win_probability,
            item.away_win_probability,
            item.actual_winner or "",
            "" if item.correct is None else item.correct,
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=predictions.csv"},
    )


def _premium_feature_set(plan: Plan) -> PremiumFeatureSet:
    enabled = plan == Plan.pro
    return PremiumFeatureSet(
        plan=plan,
        unlimited_analysis=enabled,
        premium_models=enabled,
        downloadable_data=enabled,
        value_analysis=enabled,
        ad_free=enabled,
    )


def _require_pro(user_id: int) -> UserProfile:
    profile = get_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile was not found")
    if profile.plan != Plan.pro:
        raise HTTPException(status_code=402, detail="This feature requires Pro.")
    return profile


def _value_picks(sport: Sport, days: int) -> list[BettingValuePick]:
    picks: list[BettingValuePick] = []
    for game in list_upcoming_games(sport, days=min(max(days, 1), 30)):
        prediction = predict_game(game_to_prediction_request(game))
        pick = _value_pick_for_game(game, prediction)
        if pick is not None:
            picks.append(pick)
    return sorted(picks, key=lambda item: item.edge or -1, reverse=True)[:20]


def _value_pick_for_game(game: GameSnapshot, prediction: PredictionResponse) -> BettingValuePick | None:
    predicted_home = prediction.predicted_winner == game.home_team.name
    model_probability = prediction.calibrated_home_win_probability if predicted_home else 1 - prediction.calibrated_home_win_probability
    moneyline = game.home_team.moneyline if predicted_home else game.away_team.moneyline
    implied = _american_implied_probability(moneyline) if moneyline is not None else None
    edge = round(model_probability - implied, 4) if implied is not None else None
    note = "No sportsbook odds available; value edge cannot be calculated."
    if edge is not None:
        note = "Positive model edge versus implied odds." if edge > 0 else "No positive model edge versus implied odds."
    return BettingValuePick(
        game_id=game.id,
        sport=game.sport,
        game_name=game.name,
        predicted_winner=prediction.predicted_winner,
        model_probability=round(model_probability, 4),
        implied_probability=implied,
        edge=edge,
        moneyline=moneyline,
        note=note,
    )


def _american_implied_probability(moneyline: int) -> float:
    if moneyline < 0:
        return round(abs(moneyline) / (abs(moneyline) + 100), 4)
    return round(100 / (moneyline + 100), 4)
