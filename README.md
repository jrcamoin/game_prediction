<<<<<<< HEAD
# game_prediction
Webapp to predict upcoming sporting events
=======
# Sports Game Winner Predictor

Initial codebase for a web app that predicts likely winners of sports games.

The app has:

- `backend/`: FastAPI service with a prediction endpoint.
- `frontend/`: React + Vite UI for entering game inputs and viewing predictions.

The first model is intentionally transparent and deterministic. It combines team rating, recent form, injuries, rest days, home field, travel, and optional market odds into a win probability. This is a practical baseline that can later be replaced or calibrated with historical game data.

## Requirements

- Python 3.11+
- Node.js 20+

## Run The Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs will be available at `http://localhost:8000/docs`.

## Run The Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and calls the backend at `http://localhost:8000`.

## Useful Endpoints

- `GET /health`
- `POST /api/predict`
- `POST /api/predict/batch`

## Next Steps

- Add persistence for teams, games, and prediction history.
- Ingest historical schedules, results, injuries, and betting lines.
- Train sport-specific models and calibrate probabilities.
- Add authentication and saved leagues.
>>>>>>> d626e53 (Initial sports prediction webapp)
