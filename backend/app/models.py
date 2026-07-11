from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Sport(StrEnum):
    football = "football"
    basketball = "basketball"
    baseball = "baseball"
    hockey = "hockey"
    soccer = "soccer"


class TeamInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    rating: float = Field(1500, ge=1000, le=2200, description="Elo-like team strength rating")
    recent_wins: int = Field(3, ge=0, le=10)
    recent_losses: int = Field(2, ge=0, le=10)
    injuries: int = Field(0, ge=0, le=20, description="Unavailable key players")
    rest_days: int = Field(3, ge=0, le=14)
    moneyline: int | None = Field(None, ge=-5000, le=5000, description="American odds")

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


class FactorBreakdown(BaseModel):
    rating: float
    recent_form: float
    injuries: float
    rest: float
    venue: float
    travel: float
    market: float


class PredictionResponse(BaseModel):
    predicted_winner: str
    home_win_probability: float
    away_win_probability: float
    confidence: str
    score: float
    factors: FactorBreakdown
    summary: str
