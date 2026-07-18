from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


FEATURE_COLUMNS = [
    "rating_edge",
    "advanced_rating_edge",
    "expected_value_edge",
    "recent_form_edge",
    "injury_edge",
    "lineup_edge",
    "rest_edge",
    "venue_edge",
    "travel_edge",
    "market_edge",
    "weather_edge",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the production XGBoost win-probability model.")
    parser.add_argument("--input", required=True, help="CSV with feature columns and a home_won target column.")
    parser.add_argument("--output", default="artifacts/xgboost_win_model.joblib", help="Model artifact path.")
    args = parser.parse_args()

    try:
        import joblib
        import pandas as pd
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise SystemExit(
            "Install model dependencies first: python -m pip install -r requirements-model.txt"
        ) from exc

    data = pd.read_csv(args.input)
    missing = [column for column in [*FEATURE_COLUMNS, "home_won"] if column not in data.columns]
    if missing:
        raise SystemExit(f"Training data is missing required columns: {', '.join(missing)}")

    x = data[FEATURE_COLUMNS]
    y = data["home_won"].astype(int)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, shuffle=False)

    base_model, model_family = _base_model()
    calibrated = CalibratedClassifierCV(base_model, method="isotonic", cv=3)
    calibrated.fit(x_train, y_train)

    probabilities = calibrated.predict_proba(x_test)[:, 1]
    metrics = {
        "auc": roc_auc_score(y_test, probabilities),
        "log_loss": log_loss(y_test, probabilities),
        "brier": brier_score_loss(y_test, probabilities),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": calibrated, "features": FEATURE_COLUMNS, "metrics": metrics, "family": model_family}, output_path)

    print(f"Wrote {output_path}")
    print(f"Model family: {model_family}")
    print({key: round(value, 4) for key, value in metrics.items()})


def _base_model():
    try:
        from xgboost import XGBClassifier

        return (
            XGBClassifier(
                n_estimators=350,
                max_depth=3,
                learning_rate=0.035,
                subsample=0.86,
                colsample_bytree=0.86,
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=42,
            ),
            "xgboost",
        )
    except Exception as exc:
        from sklearn.ensemble import HistGradientBoostingClassifier

        print(f"XGBoost unavailable; falling back to sklearn HistGradientBoostingClassifier: {exc}")
        return (
            HistGradientBoostingClassifier(
                max_iter=350,
                learning_rate=0.035,
                max_leaf_nodes=15,
                l2_regularization=0.05,
                random_state=42,
            ),
            "sklearn-hist-gradient-boosting",
        )


if __name__ == "__main__":
    main()
