import math
import random

import pandas as pd


SEVERITY_BY_CLASS = {
    "A": ("Low", 1),
    "B": ("Low", 1),
    "C": ("Moderate", 2),
    "M": ("High", 3),
    "X": ("Extreme", 4),
}


def flare_severity(class_type: str) -> tuple[str, int]:
    flare_band = class_type[:1].upper()
    return SEVERITY_BY_CLASS.get(flare_band, ("Unknown", 0))


def generate_demo_forecast(
    history: pd.DataFrame,
    *,
    now: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Create a reproducible, empirical 24-hour demo forecast from historical flares."""
    required_columns = {"beginTime", "classType"}
    if not required_columns.issubset(history.columns):
        raise ValueError("Flare history must include beginTime and classType columns")

    events = history.loc[:, ["beginTime", "classType"]].copy()
    events["beginTime"] = pd.to_datetime(
        events["beginTime"], unit="ms", utc=True, errors="coerce"
    )
    events["classType"] = events["classType"].astype("string").str.upper()
    events = events.dropna(subset=["beginTime", "classType"])
    events = events.loc[events["classType"].str.match(r"^[ABCMX]\d+(?:\.\d+)?$", na=False)]
    if events.empty:
        raise ValueError("Flare history contains no valid classType observations")

    current_time = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if current_time.tzinfo is None:
        current_time = current_time.tz_localize("UTC")
    else:
        current_time = current_time.tz_convert("UTC")

    first_day = events["beginTime"].min().floor("D")
    last_day = events["beginTime"].max().floor("D")
    observed_days = max((last_day - first_day).days + 1, 1)
    global_hourly_rate = len(events) / (observed_days * 24)
    hourly_counts = events["beginTime"].dt.hour.value_counts()
    smoothing_days = 30

    forecast_hours = pd.date_range(
        current_time.floor("h") + pd.Timedelta(hours=1),
        periods=24,
        freq="h",
    )
    random_generator = random.Random(int(forecast_hours[0].value // 1_000_000_000))
    class_counts = events["classType"].value_counts()
    class_values = class_counts.index.tolist()
    class_weights = class_counts.tolist()

    predictions = []
    for hour in forecast_hours:
        observed_count = int(hourly_counts.get(hour.hour, 0))
        smoothed_rate = (
            observed_count + global_hourly_rate * smoothing_days
        ) / (observed_days + smoothing_days)
        flare_probability = 1 - math.exp(-smoothed_rate)
        likely_class = random_generator.choices(class_values, weights=class_weights, k=1)[0]
        predicted_class = (
            likely_class if random_generator.random() < flare_probability else "No flare expected"
        )
        severity, severity_score = flare_severity(likely_class)
        predictions.append({
            "Hour (UTC)": hour,
            "Predicted class": predicted_class,
            "Likely class if a flare occurs": likely_class,
            "Flare probability (%)": round((flare_probability * 100), 1),
            "Likely severity if a flare occurs": severity,
            "Severity score if a flare occurs": severity_score,
            "Predicted severity": severity if predicted_class != "No flare expected" else "Quiet",
            "Predicted severity score": severity_score if predicted_class != "No flare expected" else 0,
        })

    return pd.DataFrame(predictions)