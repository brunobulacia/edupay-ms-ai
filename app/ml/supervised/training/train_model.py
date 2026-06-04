import os
import json
from pathlib import Path
import joblib
import lightgbm as lgb
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score

from .prepare_dataset import generate_dataset

FEATURES = [
    "avg_days_late_last_3_months",
    "max_days_late_ever",
    "months_paid_on_time_ratio",
    "consecutive_late_payments",
    "has_paid_annual_ever",
    "preferred_payment_method_qr",
    "preferred_payment_method_stripe",
    "preferred_payment_method_blockchain",
    "avg_payment_day_of_month",
    "uses_mobile_app",
    "num_students",
    "years_enrolled",
    "has_discount",
    "month",
    "is_after_carnaval",
    "months_remaining_year",
]
TARGET = "will_be_late_next_month"
MODEL_VERSION = "lgbm-v1.0.0"


def train(output_dir: str = "models_store/mora_predictor/v1.0.0") -> dict:
    print("[TRAIN] Generating dataset...")
    df = generate_dataset(n_families=5000)

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    print(f"[TRAIN] Train: {len(X_train)} | Test: {len(X_test)}")
    print(f"[TRAIN] Late ratio train: {y_train.mean():.2%}")

    model = lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        verbose=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(False)],
    )

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    metrics = {
        "aucRoc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "trainingSamples": len(X_train),
    }
    print(f"[TRAIN] Metrics: {metrics}")

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    model_path = os.path.join(output_dir, "model.pkl")
    meta_path = os.path.join(output_dir, "meta.json")

    joblib.dump(model, model_path)
    with open(meta_path, "w") as f:
        json.dump({
            "version": MODEL_VERSION,
            "features": FEATURES,
            "metrics": metrics,
        }, f, indent=2)

    print(f"[TRAIN] Model saved to {model_path}")
    return metrics


if __name__ == "__main__":
    train()
