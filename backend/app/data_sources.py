from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models import DataSourceStatus, GameResult, GameSnapshot, PredictionRequest, Sport, TeamSnapshot
from app.providers.golf import list_golf_matchups
from app.providers.ufc import list_ufc_bouts
from app.statbomb import statbomb_detail, statbomb_enabled, team_xg_profiles


ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"
ODDS_BASE_URL = "https://api.the-odds-api.com/v4/sports"

ESPN_LEAGUES: dict[Sport, tuple[str, str]] = {
    Sport.football: ("football", "nfl"),
    Sport.basketball: ("basketball", "nba"),
    Sport.baseball: ("baseball", "mlb"),
    Sport.hockey: ("hockey", "nhl"),
    Sport.soccer: ("soccer", "usa.1"),
}

PROVIDER_SUPPORTED_SPORTS = {Sport.golf, Sport.ufc}
SCHEDULE_SUPPORTED_SPORTS = set(ESPN_LEAGUES) | PROVIDER_SUPPORTED_SPORTS

ODDS_SPORT_KEYS: dict[Sport, str] = {
    Sport.football: "americanfootball_nfl",
    Sport.basketball: "basketball_nba",
    Sport.baseball: "baseball_mlb",
    Sport.hockey: "icehockey_nhl",
    Sport.soccer: "soccer_usa_mls",
}


@dataclass
class TeamProfile:
    id: str
    name: str
    abbreviation: str | None = None
    rating: float = 1500
    recent_results: list[bool] = field(default_factory=list)
    last_game_date: datetime | None = None

    @property
    def recent_wins(self) -> int:
        return sum(self.recent_results[-5:])

    @property
    def recent_losses(self) -> int:
        return max(0, len(self.recent_results[-5:]) - self.recent_wins)

    def rest_days(self, game_date: datetime) -> int:
        if self.last_game_date is None:
            return 3
        rest = (game_date.date() - self.last_game_date.date()).days
        return min(max(rest, 0), 14)


def source_statuses(odds_enabled: bool, odds_detail: str) -> list[DataSourceStatus]:
    return [
        DataSourceStatus(
            name="ESPN scoreboard",
            enabled=True,
            detail="Schedules, results, scores, team names, and venue flags.",
        ),
        DataSourceStatus(
            name="The Odds API",
            enabled=odds_enabled,
            detail=odds_detail,
        ),
    ]


def unsupported_schedule_statuses(sport: Sport) -> list[DataSourceStatus]:
    return [
        DataSourceStatus(
            name="Manual mode",
            enabled=True,
            detail=f"{sport.value.upper()} is available for manual predictions while live schedule integration is added.",
        ),
        DataSourceStatus(
            name="ESPN scoreboard",
            enabled=False,
            detail="No home/away schedule adapter is configured for this sport yet.",
        ),
    ]


def list_upcoming_games(sport: Sport, days: int = 14) -> list[GameSnapshot]:
    if sport == Sport.golf:
        return list_golf_matchups(days)
    if sport == Sport.ufc:
        return list_ufc_bouts(days)
    if sport not in SCHEDULE_SUPPORTED_SPORTS:
        return []

    history = _build_team_profiles(sport)
    odds = _fetch_odds_by_matchup(sport)
    game_date = datetime.now(UTC)
    games: list[GameSnapshot] = []

    for event in _fetch_events(sport, days=days, direction="future"):
        competition = _primary_competition(event)
        if competition is None:
            continue
        competitors = _competitors_by_home_away(competition)
        if "home" not in competitors or "away" not in competitors:
            continue

        event_date = _parse_date(event.get("date")) or game_date
        home = _snapshot_from_competitor(competitors["home"], history, event_date)
        away = _snapshot_from_competitor(competitors["away"], history, event_date)
        _apply_odds(home, away, odds)
        sources = source_statuses(bool(odds), _odds_detail(odds))
        if sport == Sport.soccer:
            _apply_statbomb_xg(home, away, sources)

        games.append(
            GameSnapshot(
                id=str(event.get("id", "")),
                sport=sport,
                date=event_date.isoformat(),
                name=str(event.get("name") or f"{away.name} at {home.name}"),
                home_team=home,
                away_team=away,
                neutral_site=bool(competition.get("neutralSite", False)),
                venue_name=_venue_name(competition),
                venue_city=_venue_city(competition),
                venue_state=_venue_state(competition),
                sources=sources,
            )
        )

    return games


def build_prediction_request_from_game(sport: Sport, game_id: str) -> GameSnapshot:
    for game in list_upcoming_games(sport, days=30):
        if game.id == game_id:
            return _enrich_weather(game)
    raise ValueError(f"No upcoming {sport} game found with id {game_id}")


def resolve_game_result(sport: Sport, game_id: str) -> GameResult | None:
    if sport not in SCHEDULE_SUPPORTED_SPORTS:
        return None
    events = _fetch_events(sport, days=30, direction="future") + _fetch_events(sport, days=365, direction="past")
    for event in events:
        if str(event.get("id", "")) != game_id:
            continue

        competition = _primary_competition(event)
        competitors = _competitors_by_home_away(competition or {})
        home = competitors.get("home")
        away = competitors.get("away")
        if competition is None or home is None or away is None:
            return None

        home_score = _score(home)
        away_score = _score(away)
        completed = _is_completed(competition)
        winner = None
        if completed and home_score is not None and away_score is not None and home_score != away_score:
            winner = _team_name(home if home_score > away_score else away)

        return GameResult(
            game_id=game_id,
            sport=sport,
            completed=completed,
            winner=winner,
            home_score=home_score,
            away_score=away_score,
        )

    return None


def game_to_prediction_request(game: GameSnapshot) -> PredictionRequest:
    return PredictionRequest(
        sport=game.sport,
        home_team=game.home_team,
        away_team=game.away_team,
        neutral_site=game.neutral_site,
        home_travel_miles=game.home_travel_miles,
        away_travel_miles=game.away_travel_miles,
        weather=game.weather,
    )


def _enrich_weather(game: GameSnapshot) -> GameSnapshot:
    if game.sport not in {Sport.football, Sport.baseball, Sport.soccer}:
        return game
    location = ", ".join(part for part in [game.venue_city, game.venue_state] if part)
    if not location:
        return game
    try:
        from app.weather import weather_for_location

        game.weather = weather_for_location(location, game.date, game.venue_name)
        if game.weather is not None:
            game.sources.append(
                DataSourceStatus(
                    name="Open-Meteo",
                    enabled=True,
                    detail="Venue weather forecast included for outdoor sports.",
                )
            )
        else:
            game.sources.append(
                DataSourceStatus(
                    name="Open-Meteo",
                    enabled=False,
                    detail="Weather location or forecast was unavailable for this venue.",
                )
            )
    except RuntimeError:
        game.sources.append(
            DataSourceStatus(
                name="Open-Meteo",
                enabled=False,
                detail="Weather lookup failed; prediction continued without weather.",
            )
        )
    return game


@lru_cache(maxsize=32)
def _build_team_profiles(sport: Sport, days: int = 210) -> dict[str, TeamProfile]:
    profiles: dict[str, TeamProfile] = {}
    completed_events = [
        event
        for event in _fetch_events(sport, days=days, direction="past")
        if _is_completed(_primary_competition(event))
    ]
    completed_events.sort(key=lambda event: event.get("date", ""))

    for event in completed_events:
        competition = _primary_competition(event)
        if competition is None:
            continue
        competitors = _competitors_by_home_away(competition)
        if "home" not in competitors or "away" not in competitors:
            continue

        home_profile = _profile_for_competitor(profiles, competitors["home"])
        away_profile = _profile_for_competitor(profiles, competitors["away"])
        home_score = _score(competitors["home"])
        away_score = _score(competitors["away"])
        if home_score is None or away_score is None or home_score == away_score:
            continue

        home_won = home_score > away_score
        _update_elo(home_profile, away_profile, home_won, sport)
        event_date = _parse_date(event.get("date"))
        if event_date is not None:
            home_profile.last_game_date = event_date
            away_profile.last_game_date = event_date
        home_profile.recent_results.append(home_won)
        away_profile.recent_results.append(not home_won)

    return profiles


def _fetch_events(sport: Sport, days: int, direction: str) -> list[dict]:
    if sport not in SCHEDULE_SUPPORTED_SPORTS:
        return []
    today = datetime.now(UTC).date()
    start = today if direction == "future" else today - timedelta(days=days)
    end = today + timedelta(days=days) if direction == "future" else today - timedelta(days=1)
    dates = f"{start:%Y%m%d}-{end:%Y%m%d}"
    category, league = ESPN_LEAGUES[sport]
    url = f"{ESPN_BASE_URL}/{category}/{league}/scoreboard?{urlencode({'dates': dates, 'limit': 1000})}"
    payload = _get_json(url)
    return list(payload.get("events", []))


def _fetch_odds_by_matchup(sport: Sport) -> dict[tuple[str, str], tuple[int | None, int | None]]:
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key or sport not in ODDS_SPORT_KEYS:
        return {}

    sport_key = ODDS_SPORT_KEYS[sport]
    params = urlencode(
        {
            "apiKey": api_key,
            "regions": os.getenv("ODDS_REGIONS", "us"),
            "markets": "h2h",
            "oddsFormat": "american",
        }
    )
    try:
        events = _get_json(f"{ODDS_BASE_URL}/{sport_key}/odds?{params}")
    except RuntimeError:
        return {}

    odds: dict[tuple[str, str], tuple[int | None, int | None]] = {}
    for event in events:
        home_team = str(event.get("home_team", ""))
        away_team = str(event.get("away_team", ""))
        home_price, away_price = _moneyline_from_event(event, home_team, away_team)
        if home_team and away_team:
            odds[(_normalize_team_name(home_team), _normalize_team_name(away_team))] = (home_price, away_price)
    return odds


def _moneyline_from_event(event: dict, home_team: str, away_team: str) -> tuple[int | None, int | None]:
    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market.get("key") != "h2h":
                continue
            prices = {outcome.get("name"): outcome.get("price") for outcome in market.get("outcomes", [])}
            return prices.get(home_team), prices.get(away_team)
    return None, None


def _snapshot_from_competitor(
    competitor: dict,
    profiles: dict[str, TeamProfile],
    game_date: datetime,
) -> TeamSnapshot:
    profile = _profile_for_competitor(profiles, competitor)
    recent_wins = profile.recent_wins
    recent_losses = profile.recent_losses
    if recent_wins + recent_losses == 0:
        recent_wins = 3
        recent_losses = 2

    return TeamSnapshot(
        id=profile.id,
        name=profile.name,
        abbreviation=profile.abbreviation,
        rating=round(profile.rating, 1),
        recent_wins=recent_wins,
        recent_losses=recent_losses,
        injuries=0,
        rest_days=profile.rest_days(game_date),
        moneyline=None,
        source="ESPN scoreboard",
    )


def _apply_odds(
    home: TeamSnapshot,
    away: TeamSnapshot,
    odds: dict[tuple[str, str], tuple[int | None, int | None]],
) -> None:
    matchup = (_normalize_team_name(home.name), _normalize_team_name(away.name))
    home_moneyline, away_moneyline = odds.get(matchup, (None, None))
    home.moneyline = home_moneyline
    away.moneyline = away_moneyline
    if home_moneyline is not None or away_moneyline is not None:
        home.source = "ESPN scoreboard + The Odds API"
        away.source = "ESPN scoreboard + The Odds API"


def _apply_statbomb_xg(home: TeamSnapshot, away: TeamSnapshot, sources: list[DataSourceStatus]) -> None:
    profiles = team_xg_profiles()
    home_profile = profiles.get(_normalize_team_name(home.name))
    away_profile = profiles.get(_normalize_team_name(away.name))
    if home_profile and away_profile:
        home.expected_value_for = home_profile.xg_for
        home.expected_value_against = home_profile.xg_against
        away.expected_value_for = away_profile.xg_for
        away.expected_value_against = away_profile.xg_against
        home.source = f"{home.source} + StatsBomb xG"
        away.source = f"{away.source} + StatsBomb xG"
        sources.append(
            DataSourceStatus(
                name="StatsBomb open data",
                enabled=True,
                detail=f"xG profiles matched for both teams from {home_profile.matches + away_profile.matches} team-match samples.",
            )
        )
        return

    sources.append(
        DataSourceStatus(
            name="StatsBomb open data",
            enabled=False,
            detail=statbomb_detail() if statbomb_enabled() else "Optional soccer xG enrichment is not configured.",
        )
    )


def _profile_for_competitor(profiles: dict[str, TeamProfile], competitor: dict) -> TeamProfile:
    team = competitor.get("team", {})
    team_id = str(team.get("id") or team.get("uid") or team.get("displayName"))
    if team_id not in profiles:
        profiles[team_id] = TeamProfile(
            id=team_id,
            name=str(team.get("displayName") or team.get("name") or "Unknown Team"),
            abbreviation=team.get("abbreviation"),
        )
    return profiles[team_id]


def _team_name(competitor: dict) -> str:
    team = competitor.get("team", {})
    return str(team.get("displayName") or team.get("name") or "Unknown Team")


def _venue_name(competition: dict) -> str | None:
    venue = competition.get("venue") or {}
    return venue.get("fullName")


def _venue_city(competition: dict) -> str | None:
    venue = competition.get("venue") or {}
    address = venue.get("address") or {}
    return address.get("city")


def _venue_state(competition: dict) -> str | None:
    venue = competition.get("venue") or {}
    address = venue.get("address") or {}
    return address.get("state")


def _update_elo(home: TeamProfile, away: TeamProfile, home_won: bool, sport: Sport) -> None:
    home_field_edge = 35 if sport in {Sport.baseball, Sport.hockey} else 55
    expected_home = 1 / (1 + 10 ** ((away.rating - (home.rating + home_field_edge)) / 400))
    actual_home = 1.0 if home_won else 0.0
    margin = abs(actual_home - expected_home)
    k_factor = 18 + margin * 14
    delta = k_factor * (actual_home - expected_home)
    home.rating += delta
    away.rating -= delta


def _primary_competition(event: dict | None) -> dict | None:
    if not event:
        return None
    competitions = event.get("competitions") or []
    return competitions[0] if competitions else None


def _competitors_by_home_away(competition: dict) -> dict[str, dict]:
    competitors: dict[str, dict] = {}
    for competitor in competition.get("competitors", []):
        home_away = competitor.get("homeAway")
        if home_away in {"home", "away"}:
            competitors[home_away] = competitor
    return competitors


def _is_completed(competition: dict | None) -> bool:
    if competition is None:
        return False
    status = competition.get("status", {}).get("type", {})
    return bool(status.get("completed")) or str(status.get("name", "")).lower() == "status_final"


def _score(competitor: dict) -> int | None:
    try:
        return int(float(competitor.get("score", "")))
    except (TypeError, ValueError):
        return None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _get_json(url: str) -> dict | list:
    request = Request(url, headers={"User-Agent": "game-predictor/0.2"})
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Data source request failed: {exc}") from exc


def _normalize_team_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _odds_detail(odds: dict[tuple[str, str], tuple[int | None, int | None]]) -> str:
    if odds:
        return "Moneyline odds merged from configured API key."
    if os.getenv("ODDS_API_KEY"):
        return "Configured, but no matching moneyline odds were returned."
    return "Set ODDS_API_KEY to merge live moneyline odds."
