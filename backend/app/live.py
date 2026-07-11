from __future__ import annotations

from datetime import UTC, datetime

from app.data_sources import ESPN_LEAGUES, _get_json
from app.models import (
    LiveEvent,
    LiveGameState,
    LiveMomentumPoint,
    LivePlayerStat,
    LiveTeamScore,
    LiveWinProbabilityPoint,
    Sport,
)


def get_live_game_state(sport: Sport, game_id: str) -> LiveGameState:
    category, league = ESPN_LEAGUES[sport]
    payload = _get_json(f"https://site.api.espn.com/apis/site/v2/sports/{category}/{league}/summary?event={game_id}")
    if not isinstance(payload, dict):
        raise RuntimeError("Live game payload was invalid")

    competition = (payload.get("header", {}).get("competitions") or [{}])[0]
    competitors = _competitors(competition)
    home = _team_score(competitors["home"])
    away = _team_score(competitors["away"])
    plays = payload.get("plays") or []
    status = competition.get("status", {})
    status_type = status.get("type", {})
    timeline = _timeline(plays)
    win_probability = _win_probability(payload, timeline, home.score, away.score)
    momentum = _momentum(win_probability, timeline)
    home_probability = win_probability[-1].home_win_probability if win_probability else _score_probability(home.score, away.score, 0.5)

    return LiveGameState(
        game_id=game_id,
        sport=sport,
        name=str(payload.get("header", {}).get("name") or f"{away.name} at {home.name}"),
        status=str(status_type.get("detail") or status_type.get("description") or "Unknown"),
        status_state=str(status_type.get("state") or "pre"),
        clock=status.get("displayClock"),
        period=status.get("displayPeriod") or status.get("periodPrefix"),
        home_team=home,
        away_team=away,
        home_win_probability=round(home_probability, 4),
        predicted_winner=home.name if home_probability >= 0.5 else away.name,
        win_probability=win_probability,
        momentum=momentum,
        timeline=timeline[-20:],
        team_stats=_team_stats(payload),
        player_stats=_player_stats(payload),
        expected_updates=_expected_updates(payload, sport, home_probability),
        last_updated=datetime.now(UTC).isoformat(),
    )


def _competitors(competition: dict) -> dict[str, dict]:
    mapped = {}
    for competitor in competition.get("competitors", []):
        mapped[competitor.get("homeAway")] = competitor
    if "home" not in mapped or "away" not in mapped:
        raise RuntimeError("Live game competitors were unavailable")
    return mapped


def _team_score(competitor: dict) -> LiveTeamScore:
    team = competitor.get("team", {})
    records = competitor.get("record") or []
    return LiveTeamScore(
        id=str(team.get("id") or competitor.get("id") or ""),
        name=str(team.get("displayName") or team.get("name") or "Unknown Team"),
        abbreviation=team.get("abbreviation"),
        home_away=str(competitor.get("homeAway") or ""),
        score=_int(competitor.get("score")),
        record=records[0].get("displayValue") if records else None,
    )


def _timeline(plays: list[dict]) -> list[LiveEvent]:
    events = []
    for index, play in enumerate(plays):
        text = str(play.get("text") or play.get("type", {}).get("text") or "Game event")
        home_score = _int(play.get("homeScore"))
        away_score = _int(play.get("awayScore"))
        period = play.get("period", {})
        importance = abs(_int(play.get("scoreValue"))) + (1.0 if play.get("scoringPlay") else 0.0)
        events.append(
            LiveEvent(
                id=str(play.get("id") or index),
                text=text,
                clock=play.get("clock", {}).get("displayValue") if isinstance(play.get("clock"), dict) else play.get("wallclock"),
                period=period.get("displayValue") if isinstance(period, dict) else None,
                home_score=home_score,
                away_score=away_score,
                scoring_play=bool(play.get("scoringPlay", False)),
                importance=round(importance, 2),
            )
        )
    return events


def _win_probability(payload: dict, timeline: list[LiveEvent], home_score: int, away_score: int) -> list[LiveWinProbabilityPoint]:
    raw_points = payload.get("winprobability") or []
    points = []
    for index, point in enumerate(raw_points):
        home_probability = point.get("homeWinPercentage")
        if home_probability is None:
            home_probability = point.get("homeWinProbability")
        if home_probability is None:
            continue
        if home_probability > 1:
            home_probability = home_probability / 100
        points.append(
            LiveWinProbabilityPoint(
                sequence=index,
                label=str(point.get("displayText") or point.get("playId") or index + 1),
                home_win_probability=round(float(home_probability), 4),
            )
        )
    if points:
        return points[-80:]

    synthetic = []
    for index, event in enumerate(timeline):
        synthetic.append(
            LiveWinProbabilityPoint(
                sequence=index,
                label=event.period or str(index + 1),
                home_win_probability=round(_score_probability(event.home_score, event.away_score, 0.5), 4),
            )
        )
    if not synthetic:
        synthetic.append(
            LiveWinProbabilityPoint(
                sequence=0,
                label="Now",
                home_win_probability=round(_score_probability(home_score, away_score, 0.5), 4),
            )
        )
    return synthetic[-80:]


def _momentum(probabilities: list[LiveWinProbabilityPoint], timeline: list[LiveEvent]) -> list[LiveMomentumPoint]:
    points = []
    previous = probabilities[0].home_win_probability if probabilities else 0.5
    for point in probabilities:
        delta = point.home_win_probability - previous
        points.append(
            LiveMomentumPoint(
                sequence=point.sequence,
                label=point.label,
                home_momentum=round(delta * 100, 2),
            )
        )
        previous = point.home_win_probability

    if len(points) <= 1 and timeline:
        for index, event in enumerate(timeline[-20:]):
            points.append(
                LiveMomentumPoint(
                    sequence=index,
                    label=event.period or str(index + 1),
                    home_momentum=round((event.home_score - event.away_score) * 0.8, 2),
                )
            )
    return points[-40:]


def _team_stats(payload: dict) -> dict[str, dict[str, str]]:
    stats_by_team = {}
    for team_entry in payload.get("boxscore", {}).get("teams", []):
        team = team_entry.get("team", {})
        team_name = str(team.get("displayName") or team.get("abbreviation") or "Team")
        compact = {}
        for category in team_entry.get("statistics", [])[:2]:
            for stat in category.get("stats", [])[:8]:
                abbreviation = stat.get("abbreviation") or stat.get("shortDisplayName") or stat.get("name")
                compact[str(abbreviation)] = str(stat.get("displayValue") or stat.get("value") or "0")
        stats_by_team[team_name] = compact
    return stats_by_team


def _player_stats(payload: dict) -> list[LivePlayerStat]:
    stats = []
    for athlete_group in payload.get("boxscore", {}).get("players", []):
        team_name = str(athlete_group.get("team", {}).get("displayName") or athlete_group.get("team", {}).get("abbreviation") or "Team")
        for category in athlete_group.get("statistics", [])[:2]:
            labels = category.get("labels") or []
            for athlete in category.get("athletes", [])[:6]:
                player = athlete.get("athlete", {})
                values = athlete.get("stats") or []
                stat_line = " · ".join(f"{label} {value}" for label, value in zip(labels[:4], values[:4]))
                if stat_line:
                    stats.append(
                        LivePlayerStat(
                            team=team_name,
                            player=str(player.get("displayName") or player.get("shortName") or "Player"),
                            stat_line=stat_line,
                        )
                    )
    return stats[:20]


def _expected_updates(payload: dict, sport: Sport, home_probability: float) -> list[str]:
    updates = [f"Live home win probability: {home_probability:.1%}."]
    situation = payload.get("situation") or {}
    for note in situation.get("situationNotes", [])[:3]:
        if note.get("text"):
            updates.append(str(note["text"]))
    if sport == Sport.soccer:
        updates.append("Expected goals are approximated from ESPN events until an xG provider is connected.")
    elif sport in {Sport.football, Sport.basketball}:
        updates.append("Expected points are approximated from score state and live win probability.")
    elif sport == Sport.baseball:
        updates.append("Expected runs use ESPN situation notes when available.")
    return updates


def _score_probability(home_score: int, away_score: int, base: float) -> float:
    return max(0.03, min(0.97, base + (home_score - away_score) * 0.045))


def _int(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
