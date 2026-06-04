import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def generate_family_history(family_id: int, num_months: int = 24) -> list[dict]:
    profile = np.random.choice(
        ["puntual", "regular", "irregular", "moroso"],
        p=[0.30, 0.40, 0.20, 0.10],
    )

    payments = []
    for offset in range(num_months):
        month_date = datetime(2024, 1, 1) + timedelta(days=30 * offset)

        if profile == "puntual":
            days_late = np.random.normal(-3, 1.5)
        elif profile == "regular":
            days_late = np.random.normal(3, 2)
        elif profile == "irregular":
            days_late = np.random.normal(8, 8)
        else:
            days_late = np.random.normal(20, 10)

        payments.append({
            "family_id": family_id,
            "month": month_date.month,
            "year": month_date.year,
            "days_late": max(-15, float(days_late)),
            "paid": np.random.random() > (0.02 if profile != "moroso" else 0.15),
            "profile": profile,
            "payment_method": np.random.choice(["QR", "STRIPE", "BLOCKCHAIN"], p=[0.5, 0.4, 0.1]),
            "uses_mobile_app": np.random.random() > 0.3,
            "num_students": np.random.randint(1, 5),
            "years_enrolled": np.random.randint(1, 10),
            "has_discount": np.random.random() > 0.7,
        })
    return payments


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.groupby("family_id").apply(_compute_features, include_groups=False).reset_index()
    return agg


def _compute_features(group: pd.DataFrame) -> pd.Series:
    sorted_g = group.sort_values(["year", "month"])
    last3 = sorted_g.tail(3)

    consecutive_late = 0
    for _, row in sorted_g.tail(6).iterrows():
        if row["days_late"] > 0:
            consecutive_late += 1
        else:
            consecutive_late = 0

    method = sorted_g["payment_method"].mode()[0]

    # target: did the LAST month come in late?
    target = int(sorted_g.iloc[-1]["days_late"] > 0)

    return pd.Series({
        "avg_days_late_last_3_months": last3["days_late"].mean(),
        "max_days_late_ever": sorted_g["days_late"].max(),
        "months_paid_on_time_ratio": (sorted_g["days_late"] <= 0).mean(),
        "consecutive_late_payments": consecutive_late,
        "has_paid_annual_ever": int(sorted_g["paid"].all()),
        "preferred_payment_method_qr": int(method == "QR"),
        "preferred_payment_method_stripe": int(method == "STRIPE"),
        "preferred_payment_method_blockchain": int(method == "BLOCKCHAIN"),
        "avg_payment_day_of_month": (sorted_g["days_late"] + 10).clip(1, 31).mean(),
        "uses_mobile_app": int(sorted_g["uses_mobile_app"].iloc[-1]),
        "num_students": int(sorted_g["num_students"].iloc[-1]),
        "years_enrolled": int(sorted_g["years_enrolled"].iloc[-1]),
        "has_discount": int(sorted_g["has_discount"].iloc[-1]),
        "month": int(sorted_g["month"].iloc[-1]),
        "is_after_carnaval": int(sorted_g["month"].iloc[-1] in [2, 3]),
        "months_remaining_year": 12 - int(sorted_g["month"].iloc[-1]),
        "profile": sorted_g["profile"].iloc[-1],
        "will_be_late_next_month": target,
    })


def generate_dataset(n_families: int = 5000, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    all_payments = []
    for fid in range(n_families):
        all_payments.extend(generate_family_history(fid))
    raw = pd.DataFrame(all_payments)
    return build_features(raw)
