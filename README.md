# Sports Game Winner Predictor

Web app for predicting upcoming sporting events.

The app includes:

- `backend/`: FastAPI service with prediction, live game, community, premium, and history endpoints.
- `frontend/`: React + Vite UI for selecting games, running predictions, and reviewing results.
- SQLite-backed local profiles, favorites, prediction history, comments, contests, and premium prototype state.
- First-class prediction support for football, basketball, baseball, hockey, soccer, golf, and UFC.
- Optional soccer xG enrichment from StatsBomb open data.
- ESPN-backed golf matchup and UFC fight-card providers with file and sample fallbacks for local development.
- A stacked tree ensemble slot that can be replaced with a trained XGBoost artifact once historical training data is available.
- A product-style dashboard shell with sport readiness, model status, account, community, premium, and history sections.
- GitHub Actions CI for backend tests and frontend builds.

## Requirements

- Python 3.12 is recommended for the backend.
- Node.js 20+ is recommended for the frontend.

Python 3.14 is not currently supported by the pinned backend dependency stack because `pydantic-core==2.33.2` does not provide compatible support for it.

## First-Time Setup

Install frontend packages:

```bash
cd frontend
npm install
```

Create the backend virtualenv with Python 3.12 and install packages:

```bash
cd backend
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If your Python 3.12 is on your `PATH`, this shorter command also works:

```bash
python3.12 -m venv .venv
```

## Run Locally

Start the backend in one terminal:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

The API docs will be available at `http://localhost:8000/docs`.

Start the frontend in a second terminal:

```bash
cd frontend
npm start
```

The frontend runs at `http://localhost:5173` and calls the backend at `http://localhost:8000`.

## Optional Odds Source

```bash
export ODDS_API_KEY=your_api_key
export ODDS_REGIONS=us
```

Without an odds key, live predictions still work from ESPN data and the market factor remains neutral.

## Optional StatsBomb Soccer xG

StatsBomb open data can enrich soccer predictions with team xG-for and xG-against profiles. The preferred local setup is to clone or download the StatsBomb open-data repository and point the backend to its `data` folder:

```bash
export STATBOMB_OPEN_DATA_DIR=/path/to/statsbomb/open-data/data
```

You can limit load time with:

```bash
export STATBOMB_COMPETITION_IDS=16,43
export STATBOMB_SEASON_IDS=4,3
export STATBOMB_MAX_MATCHES=250
```

For quick experiments without a local clone:

```bash
export STATBOMB_ENABLE_REMOTE=1
```

Remote mode fetches raw JSON from GitHub and should be treated as slower and less reliable than a local data folder.

Manual predictions can also use the `expected_value_for` and `expected_value_against` team fields. For soccer, treat those as xG. For golf or UFC, use them as your sport-specific expected-output metric until dedicated provider adapters are added.

## Golf And UFC Feeds

Golf and UFC first try ESPN public scoreboard feeds. If ESPN is unavailable, they use file-backed providers. If no file is configured, the backend exposes sample local matchups so the full real-game flow still works.

```bash
export GOLF_EVENTS_JSON=/path/to/golf-events.json
export UFC_EVENTS_JSON=/path/to/ufc-events.json
```

To force local JSON/sample mode:

```bash
export GOLF_DISABLE_ESPN=1
export UFC_DISABLE_ESPN=1
```

Each JSON file may be a list or an object with an `events` list. Use fields like `id`, `date`, `name`, `home_name`, `away_name`, `home_rating`, `away_rating`, `home_moneyline`, `away_moneyline`, `home_expected_value_for`, and `away_expected_value_against`.

## Optional Auth Token

For deployed environments, set a shared bearer token:

```bash
export APP_AUTH_TOKEN=change-me
```

The current app exposes `GET /api/auth/session` as an integration point. Local development works without a token.

Issue an expiring bearer session token:

```bash
curl -X POST 'http://localhost:8000/api/auth/token?subject=admin' \
  -H "Authorization: Bearer $APP_AUTH_TOKEN"
```

## Optional Trained XGBoost Model

The running app uses a deterministic stacked-tree scaffold unless a trained artifact is configured:

```bash
export XGBOOST_MODEL_PATH=/path/to/xgboost_win_model.joblib
```

To train an artifact from a prepared historical feature CSV:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-model.txt
python scripts/train_xgboost.py --input data/training/win_features.csv --output artifacts/xgboost_win_model.joblib
```

To build that CSV from completed ESPN-backed games:

```bash
python scripts/build_training_dataset.py --sports football,basketball,baseball,hockey,soccer --days 730 --output data/training/win_features.csv
```

The training CSV must include:

```text
rating_edge, advanced_rating_edge, expected_value_edge, recent_form_edge, injury_edge,
lineup_edge, rest_edge, venue_edge, travel_edge, market_edge, weather_edge, home_won
```

Set `XGBOOST_MODEL_PATH` after training so `/api/model/status` can report the artifact as active.

On macOS, XGBoost may require OpenMP:

```bash
brew install libomp
```

If XGBoost cannot load, the trainer falls back to sklearn histogram gradient boosting and still writes a compatible tree artifact.

## Postgres Migration

SQLite remains the local default. For production Postgres:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-postgres.txt
export DATABASE_URL=postgresql://user:password@host:5432/dbname
python scripts/migrate_sqlite_to_postgres.py
```

The Postgres schema is in `backend/db/postgres_schema.sql`.

## Test And Build

Backend tests:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests
```

Frontend production build:

```bash
cd frontend
npm run build
```

CI runs both checks through `.github/workflows/ci.yml`.

## Deployment Configs

- `render.yaml` defines a Render backend service.
- `frontend/vercel.json` defines a Vercel frontend build.

## Useful Endpoints

- `GET /health`
- `GET /api/auth/session`
- `GET /api/model/status`
- `GET /api/games/upcoming?sport=baseball&days=14`
- `GET /api/games/recommendations?sport=baseball&days=14&limit=5`
- `POST /api/predict`
- `POST /api/predict/batch`
- `POST /api/predict/live/{sport}/{game_id}`
- `GET /api/predictions`
- `GET /api/predictions/summary`
- `POST /api/predictions/grade`
- `GET /api/games/result/{sport}/{game_id}`
- `GET /api/users`
- `POST /api/users`
- `GET /api/users/{user_id}/daily-feed`
- `GET /api/users/{user_id}/favorites`
- `POST /api/users/{user_id}/favorites`
- `PUT /api/users/{user_id}/notifications`
- `GET /api/simulations/season?sport=baseball&days=30&simulations=1000`
- `GET /api/live/{sport}/{game_id}`
- `GET /api/community`
- `GET /api/premium/features/{user_id}`
- `POST /api/premium/upgrade/{user_id}`
- `GET /api/premium/performance?user_id={user_id}`
- `GET /api/premium/value-picks?user_id={user_id}&sport=baseball`
- `GET /api/premium/analysis/{sport}/{game_id}?user_id={user_id}`
- `GET /api/premium/export/predictions.csv?user_id={user_id}`

## Notes

Profiles, favorites, notification preferences, and prediction history are stored in local SQLite at `backend/data/game_predictor.sqlite3` by default. Set `GAME_PREDICTOR_DB` to use a different path.

Betting analytics are informational only and not financial advice. Use only where legal.
