from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


TABLES = ["users", "favorites", "follows", "comments", "contests", "contest_entries", "predictions"]


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    sqlite_path = Path(os.getenv("GAME_PREDICTOR_DB", "data/game_predictor.sqlite3"))
    if not database_url:
        raise SystemExit("Set DATABASE_URL to your Postgres connection string.")
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Install psycopg first: python -m pip install psycopg[binary]") from exc

    schema = Path("db/postgres_schema.sql").read_text(encoding="utf-8")
    sqlite = sqlite3.connect(sqlite_path)
    sqlite.row_factory = sqlite3.Row
    with psycopg.connect(database_url) as postgres:
        with postgres.cursor() as cursor:
            cursor.execute(schema)
            for table in TABLES:
                rows = sqlite.execute(f"SELECT * FROM {table}").fetchall()
                if not rows:
                    continue
                columns = rows[0].keys()
                placeholders = ", ".join(["%s"] * len(columns))
                column_sql = ", ".join(columns)
                cursor.executemany(
                    f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                    [tuple(row[column] for column in columns) for row in rows],
                )
                print(f"Migrated {len(rows)} rows from {table}")


if __name__ == "__main__":
    main()
