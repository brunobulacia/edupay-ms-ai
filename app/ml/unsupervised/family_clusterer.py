import json
from pathlib import Path
import joblib
import numpy as np

MODEL_DIR = Path("models_store/family_clusterer/v1.0.0")

RECOMMENDED_ACTIONS = {
    "PUNTUAL_ESTRELLA": "Sin acción requerida. Ofrecer beneficios por fidelidad.",
    "REGULAR": "Recordatorio estándar día 8.",
    "IRREGULAR": "Recordatorio proactivo día 3. Ofrecer facilidades de pago.",
    "MOROSO_CRONICO": "Contacto directo día 1. Evaluar plan de cuotas.",
}


class FamilyClusterer:
    _instance: "FamilyClusterer | None" = None

    def __init__(self):
        self._km = joblib.load(MODEL_DIR / "kmeans.pkl")
        self._scaler = joblib.load(MODEL_DIR / "scaler.pkl")
        with open(MODEL_DIR / "meta.json") as f:
            meta = json.load(f)
        self._features: list[str] = meta["features"]
        self._label_map: dict[str, str] = {int(k): v for k, v in meta["labelMap"].items()}
        self._version: str = meta["version"]

    @classmethod
    def get(cls) -> "FamilyClusterer":
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
        row = np.array([[feature_values.get(f, 0) for f in self._features]])
        scaled = self._scaler.transform(row)
        cluster_id = int(self._km.predict(scaled)[0])
        label = self._label_map[cluster_id]
        return {
            "cluster": cluster_id,
            "clusterLabel": label,
            "recommendedAction": RECOMMENDED_ACTIONS[label],
        }
