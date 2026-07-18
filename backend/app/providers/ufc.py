from __future__ import annotations

import os

from app.models import GameSnapshot, Sport
from app.providers.common import game_from_record, read_provider_json


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
