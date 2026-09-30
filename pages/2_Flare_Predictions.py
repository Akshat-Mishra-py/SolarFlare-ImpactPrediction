import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.components import *
from src.dashboard.flare_prediction import generate_demo_forecast


@st.cache_data(show_spinner=False)
def load_dummy_flare_history() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parents[1] / "FlareData_2026-01-01_2026-09-29.json"
    with data_path.open(encoding="utf-8") as data_file:
        return pd.DataFrame(json.load(data_file))


@st.fragment(run_every="15m")
def render_predictions(history: pd.DataFrame) -> None:
    try:
        forecast = generate_demo_forecast(history)
    except ValueError as error:
        st.error(f"Could not generate the demo forecast: {error}")
        return

    local_now = datetime.now().astimezone()
    local_timezone = local_now.tzinfo or timezone.utc
    forecast.insert(
        1,
        "Hour (local)",
        forecast["Hour (UTC)"].dt.tz_convert(local_timezone),
    )

    predicted_events = forecast.loc[forecast["Predicted class"].ne("No flare expected")]
    peak_probability = forecast["Flare probability (%)"].max()
    peak_condition = forecast.loc[forecast["Severity score if a flare occurs"].idxmax()] # type: ignore
    peak_severity = (
        f"{peak_condition['Likely class if a flare occurs']} · "
        f"{peak_condition['Likely severity if a flare occurs']}"
    )
    history_times = pd.to_datetime(history["beginTime"], unit="ms", utc=True, errors="coerce")
    history_times = history_times.dropna()
    history_period = (
        f"{history_times.min():%b %d}–{history_times.max():%b %d, %Y}"
        if not history_times.empty
        else "Unavailable"
    )

    local_start = forecast["Hour (local)"].iloc[0]
    local_end = forecast["Hour (local)"].iloc[-1]
    utc_start = forecast["Hour (UTC)"].iloc[0]
    utc_end = forecast["Hour (UTC)"].iloc[-1]
    local_zone_name = local_now.tzname() or str(local_timezone)
    st.caption(
        f"Forecast window: {local_start:%b %d, %I:%M %p} to "
        f"{local_end:%b %d, %I:%M %p} {local_zone_name} "
        f"({utc_start:%H:%M}–{utc_end:%H:%M} UTC) · Historical sample: {history_period}"
    )

    metric_cards([
        {"label": "Hours in forecast", "value": len(forecast)},
        {"label": "Hours with simulated flare", "value": len(predicted_events)},
        {"label": "Peak hourly flare probability", "value": f"{peak_probability:.1f}%"},
        {"label": "Highest likely severity if a flare occurs", "value": peak_severity},
    ])

    class_counts = (
        forecast["Likely class if a flare occurs"]
        .value_counts()
        .rename_axis("Class type")
        .reset_index(name="Hours")
    )
    chart_data = forecast.assign(
        **{"Chart hour (local)": forecast["Hour (local)"].dt.tz_localize(None)}
    )

    probability_column, severity_column = st.columns(2)
    with probability_column:
        graph(
            chart_data,
            x="Chart hour (local)",
            y="Flare probability (%)",
            title="Hourly probability of a flare",
            chart_type="area",
        )
    with severity_column:
        graph(
            chart_data,
            x="Chart hour (local)",
            y="Severity score if a flare occurs",
            title="Likely severity class if a flare occurs",
            chart_type="bar",
        )

    section_title("Likely class by hour", "Class mix sampled from historical flare classes")
    graph(
        class_counts,
        x="Class type",
        y="Hours",
        title="Likely class mix across the forecast window",
        chart_type="bar",
    )

    section_title("24-hour forecast", "Severity bands: A/B low · C moderate · M high · X extreme")
    data_table(forecast, height=620)


def main() -> None:
    st.set_page_config(page_title="Flare Predictions", layout="wide")
    apply_dashboard_style()
    if not login_form():
        st.stop()

    Title("Flare predictions", "Hourly class and severity outlook for the next 24 hours")
    try:
        history = load_dummy_flare_history()
    except OSError as error:
        st.error(f"Could not read the supplied dummy flare dataset: {error}")
        st.stop()

    render_predictions(history)


if __name__ == "__main__":
    main()