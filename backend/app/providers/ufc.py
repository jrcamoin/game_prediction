from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from app.models import DataSourceStatus, GameSnapshot, Sport, TeamSnapshot
from app.providers.common import fetch_json_url, game_from_record, read_provider_json


ESPN_UFC_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"


SAMPLE_UFC_EVENTS = [
    {
        "id": "ufc-sample-makhachev-topuria",
        "name": "Islam Makhachev vs Ilia Topuria",
        "home_name": "Islam Makhachev",
        "away_name": "Ilia Topuria",
        "home_rating": 1665,
        "away_rating": 1620,
        "home_recent_wins": 5,
        "home_recent_losses": 0,
        "away_recent_wins": 5,
        "away_recent_losses": 0,
        "home_moneyline": -150,
        "away_moneyline": 130,
        "home_expected_value_for": 2.4,
        "home_expected_value_against": 1.2,
        "away_expected_value_for": 2.1,
        "away_expected_value_against": 1.5,
        "venue_name": "Neutral fight card",
    }
]


def list_ufc_bouts(days: int) -> list[GameSnapshot]:
    remote_games = _espn_ufc_bouts(days)
    if remote_games:
        return remote_games

    records = read_provider_json(os.getenv("UFC_EVENTS_JSON")) or SAMPLE_UFC_EVENTS
    return [
        game_from_record(
            record,
            Sport.ufc,
            "UFC fight-card provider",
            "File-backed UFC bout feed. Set UFC_EVENTS_JSON to use your own fight card.",
        )
        for record in records[: max(days, 1) * 4]
    ]


def _espn_ufc_bouts(days: int) -> list[GameSnapshot]:
    if os.getenv("UFC_DISABLE_ESPN") == "1":
        return []
    today = datetime.now(UTC).date()
    dates = f"{today:%Y%m%d}-{today + timedelta(days=days):%Y%m%d}"
    payload = fetch_json_url(f"{ESPN_UFC_SCOREBOARD}?{urlencode({'dates': dates, 'limit': 1000})}")
    games: list[GameSnapshot] = []
    for event in payload.get("events", []):
        for competition in event.get("competitions", []):
            competitors = [item for item in competition.get("competitors", []) if isinstance(item, dict)]
            if len(competitors) < 2:
                continue
            home = _ufc_snapshot(competitors[0], "UFC ESPN scoreboard")
            away = _ufc_snapshot(competitors[1], "UFC ESPN scoreboard")
            date = str(competition.get("date") or event.get("date") or datetime.now(UTC).isoformat())
            division = (competition.get("type") or {}).get("abbreviation")
            games.append(
                GameSnapshot(
                    id=str(competition.get("id") or f"{event.get('id', 'ufc')}-{home.id}-{away.id}"),
                    sport=Sport.ufc,
                    date=date,
                    name=f"{away.name} vs {home.name}",
                    home_team=home,
                    away_team=away,
                    neutral_site=True,
                    venue_name=(competition.get("venue") or {}).get("fullName"),
                    venue_city=((competition.get("venue") or {}).get("address") or {}).get("city"),
                    venue_state=((competition.get("venue") or {}).get("address") or {}).get("state"),
                    sources=[
                        DataSourceStatus(
                            name="UFC ESPN scoreboard",
                            enabled=True,
                            detail=f"Fight-card bout feed{f' · {division}' if division else ''}.",
                        )
                    ],
                )
            )
    return games


def _ufc_snapshot(competitor: dict[str, Any], source: str) -> TeamSnapshot:
    athlete = competitor.get("athlete") or {}
    wins, losses = _record(competitor)
    total = max(wins + losses, 1)
    win_rate = wins / total
    rating = 1450 + win_rate * 220 + min(wins, 25) * 3 - losses * 4
    return TeamSnapshot(
        id=str(competitor.get("id") or athlete.get("id") or athlete.get("displayName")),
        name=str(athlete.get("displayName") or athlete.get("fullName") or "Unknown fighter"),
        abbreviation=athlete.get("shortName"),
        rating=round(rating, 1),
        recent_wins=max(1, min(5, round(win_rate * 5))),
        recent_losses=max(0, 5 - max(1, min(5, round(win_rate * 5)))),
        injuries=0,
        questionable_players=0,
        starters_confirmed=1,
        projected_starters=1,
        rest_days=7,
        expected_value_for=round(1.0 + win_rate * 1.7, 2),
        expected_value_against=round(2.5 - win_rate * 1.2, 2),
        source=source,
    )


def _record(competitor: dict[str, Any]) -> tuple[int, int]:
    for record in competitor.get("records", []):
        summary = str(record.get("summary") or "")
        parts = summary.split("-")
        if len(parts) >= 2:
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                continue
    return 3, 2
