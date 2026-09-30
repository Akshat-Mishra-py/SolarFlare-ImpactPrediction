import logging
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src.dashboard.components import *
from src.data_preprocessing.donki_data_loader import Donki_dataset


@st.cache_data(ttl=300, max_entries=32, show_spinner=False)
def fetch_flares(start_date: str, end_date: str) -> pd.DataFrame:
    return Donki_dataset().fetch_flares(start_date, end_date)


def load_range(start_date: date, end_date: date) -> bool:
    try:
        with st.spinner("Loading flare observations..."):
            flares = fetch_flares(start_date.isoformat(), end_date.isoformat())
    except Exception:
        logging.exception("Failed to load DONKI flare observations")
        st.error("Flare data could not be loaded. Check the NASA API connection and try again.")
        return False

    st.session_state["flares"] = flares
    st.session_state["flare_date_range"] = (start_date, end_date)
    return True


def render_dashboard(flares: pd.DataFrame) -> None:
    if flares.empty:
        peak_class = "No events"
        peak_flux = "No events"
    else:
        valid_flux = pd.to_numeric(flares["xrayFlux"], errors="coerce").fillna(-1)
        if valid_flux.ge(0).any():
            peak_position = int(valid_flux.to_numpy().argmax())
            peak_class = str(flares["classType"].iloc[peak_position])
            peak_flux = f"{valid_flux.iloc[peak_position]:.2e} W/m²"
        else:
            peak_class = "Unavailable"
            peak_flux = "Unavailable"

    active_regions = (
        flares["activeRegionNum"].nunique(dropna=True)
        if "activeRegionNum" in flares
        else 0
    )
    metric_cards([
        {"label": "Flare count", "value": len(flares)},
        {"label": "Peak flare class", "value": peak_class},
        {"label": "Peak X-ray flux", "value": peak_flux},
        {"label": "Active regions", "value": active_regions},
    ])

    if flares.empty:
        graph(flares, title="X-ray flux over time")
        return

    timed_flares = flares.dropna(subset=["peakTime"]).sort_values("peakTime")
    daily_counts = (
        timed_flares.set_index("peakTime")
        .resample("D")
        .size()
        .rename("Flare count")
        .rename_axis("Date")
        .reset_index()
    )
    class_counts = (
        flares["flareType"]
        .value_counts()
        .rename_axis("Flare class")
        .reset_index(name="Flare count")
    )
    region_counts = (
        flares["activeRegionNum"].dropna().astype(int).value_counts().head(10)
        .sort_values()
        .rename_axis("NOAA region")
        .reset_index(name="Flare count")
    )

    left_column, right_column = st.columns(2)
    with left_column:
        graph(
            timed_flares,
            x="peakTime",
            y="xrayFlux",
            title="X-ray peak flux over time",
            chart_type="scatter",
        )
        graph(
            class_counts,
            x="Flare class",
            y="Flare count",
            title="Flare class distribution",
            chart_type="bar",
        )
    with right_column:
        graph(
            daily_counts,
            x="Date",
            y="Flare count",
            title="Daily flare count",
            chart_type="area",
        )
        graph(
            region_counts,
            x="NOAA region",
            y="Flare count",
            title="Most active regions",
            chart_type="bar",
        )

    data_table(flares, title="Flare observations")


def main() -> None:
    st.set_page_config(page_title="Solar Activity")
    apply_dashboard_style()
    if not login_form():
        st.stop()

    Title("Solar activity", "DONKI flare observations and active-region trends")
    today = date.today()
    if "flare_date_range" not in st.session_state:
        st.session_state["flare_date_range"] = (today - timedelta(days=30), today)

    current_start, current_end = st.session_state["flare_date_range"]
    selected_start, selected_end, submitted = date_range_filter(current_start, current_end)
    if "flares" not in st.session_state:
        load_range(current_start, current_end)
    elif submitted and (selected_start, selected_end) != (current_start, current_end):
        if rate_limit("flare_refresh", interval_seconds=5):
            load_range(selected_start, selected_end)
        else:
            st.warning("Please wait a few seconds before requesting another date range.")

    applied_start, applied_end = st.session_state["flare_date_range"]
    st.caption(f"Showing {applied_start:%b %d, %Y} to {applied_end:%b %d, %Y}")
    if "flares" in st.session_state:
        render_dashboard(st.session_state["flares"])


if __name__ == "__main__":
    main()
