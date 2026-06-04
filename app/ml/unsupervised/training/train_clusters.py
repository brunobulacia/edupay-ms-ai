import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from .prepare_dataset import build_family_features

FEATURES = [
    "avg_payment_day",
    "std_dev_payment_day",
    "mora_incidence",
    "annual_payer_score",
    "method_consistency",
    "months_active",
]
MODEL_VERSION = "kmeans-v1.0.0"
OUTPUT_DIR = "models_store/family_clusterer/v1.0.0"

CLUSTER_LABELS = {
    0: "PUNTUAL_ESTRELLA",
    1: "REGULAR",
    2: "IRREGULAR",
    3: "MOROSO_CRONICO",
}


def _assign_labels(km: KMeans, scaler: StandardScaler) -> dict[int, str]:
    centers = scaler.inverse_transform(km.cluster_centers_)
    center_df = pd.DataFrame(centers, columns=FEATURES)
    # avg_payment_day best separates profiles (puntual≈7, regular≈13, irregular≈18, moroso≈30)
    order = center_df["avg_payment_day"].argsort().values
    label_map = {}
    names = ["PUNTUAL_ESTRELLA", "REGULAR", "IRREGULAR", "MOROSO_CRONICO"]
    for rank, cluster_idx in enumerate(order):
        label_map[int(cluster_idx)] = names[rank]
    return label_map


def train(output_dir: str = OUTPUT_DIR) -> dict:
    print("[CLUSTER] Building family features...")
    df = build_family_features(n_families=5000)

    X = df[FEATURES].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print("[CLUSTER] Training K-Means k=4...")
    km = KMeans(n_clusters=4, random_state=42, n_init=20)
    km.fit(X_scaled)

    df["cluster"] = km.labels_
    label_map = _assign_labels(km, scaler)
    df["clusterLabel"] = df["cluster"].map(label_map)

    # Validation: cross-tab predicted vs real profile
    cross = pd.crosstab(df["profile"], df["clusterLabel"])
    print("[CLUSTER] Cross-tab profile vs cluster:\n", cross)

    # Silhouette score
    from sklearn.metrics import silhouette_score
    sil = silhouette_score(X_scaled, km.labels_)
    print(f"[CLUSTER] Silhouette score: {sil:.4f}")

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump(km, os.path.join(output_dir, "kmeans.pkl"))
    joblib.dump(scaler, os.path.join(output_dir, "scaler.pkl"))

    meta = {
        "version": MODEL_VERSION,
        "features": FEATURES,
        "labelMap": label_map,
        "silhouetteScore": round(float(sil), 4),
    }
    with open(os.path.join(output_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[CLUSTER] Models saved to {output_dir}")
    return meta


if __name__ == "__main__":
    train()
