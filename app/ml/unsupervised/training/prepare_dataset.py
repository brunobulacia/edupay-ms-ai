import numpy as np
import pandas as pd

from app.ml.supervised.training.prepare_dataset import generate_family_history


def build_family_features(n_families: int = 5000, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    records = []
    for fid in range(n_families):
        payments = generate_family_history(fid, num_months=24)
        df = pd.DataFrame(payments)

        days_late = df["days_late"]
        payment_day = (days_late + 10).clip(1, 31)

        mora_months = (days_late > 0).sum()
        total_months = len(df)

        records.append({
            "family_id": fid,
            "avg_payment_day": float(payment_day.mean()),
            "std_dev_payment_day": float(payment_day.std()),
            "mora_incidence": float(mora_months / total_months),
            "annual_payer_score": float(df["paid"].all()),
            "method_consistency": float(df["payment_method"].value_counts(normalize=True).iloc[0]),
            "months_active": total_months,
            "profile": df["profile"].iloc[0],
        })

    return pd.DataFrame(records)
