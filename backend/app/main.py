from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import PredictionRequest, PredictionResponse
from app.predictor import predict_game

app = FastAPI(
    title="Sports Game Winner Predictor API",
    version="0.1.0",
    description="Transparent baseline API for predicting sports game winners.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    return predict_game(request)


@app.post("/api/predict/batch", response_model=list[PredictionResponse])
def predict_batch(requests: list[PredictionRequest]) -> list[PredictionResponse]:
    return [predict_game(request) for request in requests]
