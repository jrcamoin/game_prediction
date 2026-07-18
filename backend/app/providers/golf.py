from __future__ import annotations

import os

from app.models import GameSnapshot, Sport
from app.providers.common import game_from_record, read_provider_json


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
