from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class Sport(StrEnum):
    football = "football"
    basketball = "basketball"
    baseball = "baseball"
    hockey = "hockey"
    soccer = "soccer"


class Plan(StrEnum):
    free = "free"
    pro = "pro"


class TeamInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    rating: float = Field(1500, ge=1000, le=2200, description="Elo-like team strength rating")
    recent_wins: int = Field(3, ge=0, le=10)
    recent_losses: int = Field(2, ge=0, le=10)
    injuries: int = Field(0, ge=0, le=20, description="Unavailable key players")
    questionable_players: int = Field(0, ge=0, le=20)
    starters_confirmed: int = Field(0, ge=0, le=20)
    projected_starters: int = Field(5, ge=0, le=30)
    rest_days: int = Field(3, ge=0, le=14)
    moneyline: int | None = Field(None, ge=-5000, le=5000, description="American odds")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("team name cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_recent_games(self) -> "TeamInput":
        if self.recent_wins + self.recent_losses == 0:
            raise ValueError("recent_wins and recent_losses cannot both be zero")
        return self


class PredictionRequest(BaseModel):
    sport: Sport = Sport.football
    home_team: TeamInput
    away_team: TeamInput
    neutral_site: bool = False
    home_travel_miles: int = Field(0, ge=0, le=10000)
    away_travel_miles: int = Field(0, ge=0, le=10000)
    weather: "WeatherSnapshot | None" = None

    @model_validator(mode="after")
    def validate_teams(self) -> "PredictionRequest":
        if self.home_team.name.casefold() == self.away_team.name.casefold():
            raise ValueError("home_team and away_team must be different")
        return self


class FactorBreakdown(BaseModel):
    rating: float
    advanced_rating: float = 0
    recent_form: float
    injuries: float
    lineup: float = 0
    rest: float
    venue: float
    travel: float
    market: float
    weather: float = 0


class ModelPrediction(BaseModel):
    name: str
    home_win_probability: float
    weight: float


class FeatureImportance(BaseModel):
    name: str
    value: float
    impact: float
    direction: str


class WeatherSnapshot(BaseModel):
    venue_name: str | None = None
    location_name: str | None = None
    temperature_f: float | None = None
    wind_mph: float | None = None
    wind_gust_mph: float | None = None
    precipitation_probability: float | None = None
    summary: str = "Weather unavailable"


class PredictionResponse(BaseModel):
    predicted_winner: str
    home_win_probability: float
    away_win_probability: float
    confidence: str
    score: float
    factors: FactorBreakdown
    ensemble: list[ModelPrediction] = []
    calibrated_home_win_probability: float
    feature_importance: list[FeatureImportance] = []
    model_notes: list[str] = []
    summary: str


class DataSourceStatus(BaseModel):
    name: str
    enabled: bool
    detail: str


class TeamSnapshot(TeamInput):
    id: str | None = None
    abbreviation: str | None = None
    source: str = "manual"


class GameSnapshot(BaseModel):
    id: str
    sport: Sport
    date: str
    name: str
    home_team: TeamSnapshot
    away_team: TeamSnapshot
    neutral_site: bool = False
    home_travel_miles: int = 0
    away_travel_miles: int = 0
    venue_name: str | None = None
    venue_city: str | None = None
    venue_state: str | None = None
    weather: WeatherSnapshot | None = None
    sources: list[DataSourceStatus]


class LivePredictionResponse(PredictionResponse):
    game: GameSnapshot


class GameResult(BaseModel):
    game_id: str
    sport: Sport
    completed: bool
    winner: str | None = None
    home_score: int | None = None
    away_score: int | None = None


class SavedPrediction(BaseModel):
    id: int
    created_at: str
    game_id: str
    sport: Sport
    game_date: str
    game_name: str
    predicted_winner: str
    home_team: str
    away_team: str
    home_win_probability: float
    away_win_probability: float
    confidence: str
    score: float
    actual_winner: str | None = None
    correct: bool | None = None
    resolved_at: str | None = None


class PredictionSummary(BaseModel):
    total: int
    resolved: int
    correct: int
    accuracy: float | None
    pending: int


class RecommendedPick(BaseModel):
    game_id: str
    sport: Sport
    game_date: str
    game_name: str
    predicted_winner: str
    probability: float
    confidence: str
    home_team: str
    away_team: str


class UserProfileCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=80)
    email: str | None = Field(None, max_length=120)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("display name cannot be blank")
        return normalized


class NotificationPreferences(BaseModel):
    daily_email: bool = False
    push_alerts: bool = False
    close_game_alerts: bool = True


class UserProfile(BaseModel):
    id: int
    display_name: str
    email: str | None = None
    created_at: str
    plan: Plan = Plan.free
    notification_preferences: NotificationPreferences


class FavoriteCreate(BaseModel):
    sport: Sport
    team_id: str | None = None
    team_name: str | None = None
    league_name: str | None = None


class Favorite(BaseModel):
    id: int
    user_id: int
    sport: Sport
    team_id: str | None = None
    team_name: str | None = None
    league_name: str | None = None
    created_at: str


class DailyFeed(BaseModel):
    profile: UserProfile | None
    favorites: list[Favorite]
    picks: list[RecommendedPick]


class SimulatedTeamSeason(BaseModel):
    team: str
    expected_wins: float
    simulated_wins: int
    playoff_seed: int


class SeasonSimulation(BaseModel):
    sport: Sport
    simulations: int
    remaining_games: int
    teams: list[SimulatedTeamSeason]


class LiveTeamScore(BaseModel):
    id: str
    name: str
    abbreviation: str | None = None
    home_away: str
    score: int
    record: str | None = None


class LiveEvent(BaseModel):
    id: str
    text: str
    clock: str | None = None
    period: str | None = None
    home_score: int
    away_score: int
    scoring_play: bool = False
    importance: float = 0


class LiveWinProbabilityPoint(BaseModel):
    sequence: int
    label: str
    home_win_probability: float


class LiveMomentumPoint(BaseModel):
    sequence: int
    label: str
    home_momentum: float


class LivePlayerStat(BaseModel):
    team: str
    player: str
    stat_line: str


class LiveGameState(BaseModel):
    game_id: str
    sport: Sport
    name: str
    status: str
    status_state: str
    clock: str | None = None
    period: str | None = None
    home_team: LiveTeamScore
    away_team: LiveTeamScore
    home_win_probability: float
    predicted_winner: str
    win_probability: list[LiveWinProbabilityPoint]
    momentum: list[LiveMomentumPoint]
    timeline: list[LiveEvent]
    team_stats: dict[str, dict[str, str]]
    player_stats: list[LivePlayerStat]
    expected_updates: list[str]
    last_updated: str


class PublicProfile(BaseModel):
    id: int
    display_name: str
    created_at: str
    followers: int
    following: int
    total_predictions: int
    resolved_predictions: int
    accuracy: float | None
    badges: list[str]


class FollowCreate(BaseModel):
    follower_id: int
    following_id: int


class Follow(BaseModel):
    id: int
    follower_id: int
    following_id: int
    created_at: str


class GameCommentCreate(BaseModel):
    user_id: int
    sport: Sport
    game_id: str
    body: str = Field(..., min_length=1, max_length=500)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("comment cannot be blank")
        return normalized


class GameComment(BaseModel):
    id: int
    user_id: int
    display_name: str
    sport: Sport
    game_id: str
    body: str
    created_at: str


class ContestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sport: Sport
    starts_at: str | None = None
    ends_at: str | None = None


class Contest(BaseModel):
    id: int
    name: str
    sport: Sport
    starts_at: str | None
    ends_at: str | None
    created_at: str


class ContestEntryCreate(BaseModel):
    user_id: int
    prediction_id: int


class ContestEntry(BaseModel):
    id: int
    contest_id: int
    user_id: int
    display_name: str
    prediction_id: int
    predicted_winner: str
    correct: bool | None = None
    created_at: str


class LeaderboardEntry(BaseModel):
    user_id: int
    display_name: str
    total_predictions: int
    resolved_predictions: int
    correct_predictions: int
    accuracy: float | None
    score: float
    badges: list[str]


class WeeklyChallenge(BaseModel):
    id: str
    title: str
    description: str
    target: int
    progress: int
    completed: bool


class CommunityDashboard(BaseModel):
    profiles: list[PublicProfile]
    leaderboard: list[LeaderboardEntry]
    contests: list[Contest]
    challenges: list[WeeklyChallenge]


class PremiumFeatureSet(BaseModel):
    plan: Plan
    unlimited_analysis: bool
    premium_models: bool
    downloadable_data: bool
    value_analysis: bool
    ad_free: bool


class ModelPerformanceReport(BaseModel):
    total_predictions: int
    resolved_predictions: int
    accuracy: float | None
    high_confidence_accuracy: float | None
    average_confidence: float | None


class BettingValuePick(BaseModel):
    game_id: str
    sport: Sport
    game_name: str
    predicted_winner: str
    model_probability: float
    implied_probability: float | None
    edge: float | None
    moneyline: int | None
    note: str


class PremiumAnalysis(BaseModel):
    game_id: str
    sport: Sport
    headline: str
    model_edge_summary: str
    risk_factors: list[str]
    suggested_watch_points: list[str]
    value_pick: BettingValuePick | None = None
    disclaimer: str
