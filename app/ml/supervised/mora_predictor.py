import json
from pathlib import Path
import joblib
import numpy as np

MODEL_DIR = Path("models_store/mora_predictor/v1.0.0")
THRESHOLDS = {"LOW": 0.4, "MEDIUM": 0.7}


class MoraPredictor:
    _instance: "MoraPredictor | None" = None

    def __init__(self):
        self._model = joblib.load(MODEL_DIR / "model.pkl")
        with open(MODEL_DIR / "meta.json") as f:
            meta = json.load(f)
        self._features: list[str] = meta["features"]
        self._version: str = meta["version"]

    @classmethod
    def get(cls) -> "MoraPredictor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def version(self) -> str:
        return self._version

    @property
    def features(self) -> list[str]:
        return self._features

    def predict(self, feature_values: dict) -> dict:
        row = [[feature_values.get(f, 0) for f in self._features]]
        prob = float(self._model.predict_proba(row)[0][1])

        if prob < THRESHOLDS["LOW"]:
            level = "LOW"
        elif prob < THRESHOLDS["MEDIUM"]:
            level = "MEDIUM"
        else:
            level = "HIGH"

        return {"riskScore": round(prob, 4), "riskLevel": level}
