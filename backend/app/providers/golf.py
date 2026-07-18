from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from app.models import DataSourceStatus, GameSnapshot, Sport, TeamSnapshot
from app.providers.common import fetch_json_url, game_from_record, read_provider_json


ESPN_GOLF_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"


SAMPLE_GOLF_EVENTS = [
    {
        "id": "golf-sample-scheffler-mcilroy",
        "name": "Scottie Scheffler vs Rory McIlroy",
        "home_name": "Scottie Scheffler",
        "away_name": "Rory McIlroy",
        "home_rating": 1690,
        "away_rating": 1655,
        "home_recent_wins": 4,
        "home_recent_losses": 1,
        "away_recent_wins": 3,
        "away_recent_losses": 2,
        "home_moneyline": -135,
        "away_moneyline": 115,
        "home_expected_value_for": 2.1,
        "home_expected_value_against": 0.9,
        "away_expected_value_for": 1.8,
        "away_expected_value_against": 1.1,
        "venue_name": "Neutral tournament matchup",
    }
]


def list_golf_matchups(days: int) -> list[GameSnapshot]:
    remote_games = _espn_golf_matchups(days)
    if remote_games:
        return remote_games

    records = read_provider_json(os.getenv("GOLF_EVENTS_JSON")) or SAMPLE_GOLF_EVENTS
    return [
        game_from_record(
            record,
            Sport.golf,
            "Golf matchup provider",
            "File-backed golf matchup feed. Set GOLF_EVENTS_JSON to use your own schedule.",
        )
        for record in records[: max(days, 1) * 4]
    ]


def _espn_golf_matchups(days: int) -> list[GameSnapshot]:
    if os.getenv("GOLF_DISABLE_ESPN") == "1":
        return []
    today = datetime.now(UTC).date()
    dates = f"{today:%Y%m%d}-{today + timedelta(days=days):%Y%m%d}"
    payload = fetch_json_url(f"{ESPN_GOLF_SCOREBOARD}?{urlencode({'dates': dates, 'limit': 1000})}")
    games: list[GameSnapshot] = []
    for event in payload.get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        competitors = [item for item in competition.get("competitors", []) if isinstance(item, dict)]
        if len(competitors) < 2:
            continue
        first, second = competitors[0], competitors[1]
        date = str(event.get("date") or competition.get("date") or datetime.now(UTC).isoformat())
        home = _golf_snapshot(first, "PGA ESPN scoreboard")
        away = _golf_snapshot(second, "PGA ESPN scoreboard")
        games.append(
            GameSnapshot(
                id=f"{event.get('id', 'pga')}-{home.id}-{away.id}",
                sport=Sport.golf,
                date=date,
                name=f"{event.get('name', 'PGA matchup')}: {away.name} vs {home.name}",
                home_team=home,
                away_team=away,
                neutral_site=True,
                venue_name=str(event.get("name") or "PGA event"),
                sources=[
                    DataSourceStatus(
                        name="PGA ESPN scoreboard",
                        enabled=True,
                        detail="Tournament field converted into top-listed head-to-head matchup.",
                    )
                ],
            )
        )
    return games


def _golf_snapshot(competitor: dict[str, Any], source: str) -> TeamSnapshot:
    athlete = competitor.get("athlete") or {}
    order = int(competitor.get("order") or 25)
    rating = max(1400, 1700 - order * 8)
    return TeamSnapshot(
        id=str(competitor.get("id") or athlete.get("id") or athlete.get("displayName")),
        name=str(athlete.get("displayName") or athlete.get("fullName") or "Unknown golfer"),
        abbreviation=athlete.get("shortName"),
        rating=rating,
        recent_wins=max(1, min(5, 6 - order // 8)),
        recent_losses=max(0, min(5, order // 8)),
        injuries=0,
        questionable_players=0,
        starters_confirmed=1,
        projected_starters=1,
        rest_days=5,
        expected_value_for=max(0.2, 2.4 - order * 0.04),
        expected_value_against=1.0,
        source=source,
    )
