import logging
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

from src.dashboard.components import *
from src.data_preprocessing.noaa_data_loader import (
    NOAA_ALERTS_URL,
    NOAADataLoader,
)


NOAA_GOES_XRAY_URL = "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json"
NOAA_SOLAR_WIND_URL = "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"
NOAA_SOLAR_MAG_URL = "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"


@st.cache_data(ttl=60, max_entries=4, show_spinner=False)
def fetch_noaa_feed(url: str) -> list[dict]:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, max_entries=4, show_spinner=False)
def fetch_noaa_flare_events() -> pd.DataFrame:
    return NOAADataLoader().fetch_flare_events()


def today_frame(records: list[dict], now: pd.Timestamp) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    if frame.empty or "time_tag" not in frame.columns:
        return frame

    frame["time_tag"] = pd.to_datetime(frame["time_tag"], utc=True, errors="coerce")
    return frame.loc[frame["time_tag"].dt.date == now.date()].dropna(subset=["time_tag"])


def today_radio_alerts(records: list[dict], now: pd.Timestamp) -> pd.DataFrame:
    alerts = pd.DataFrame(records)
    expected_columns = ["issue_datetime", "product_id", "message"]
    if alerts.empty or not {"issue_datetime", "message"}.issubset(alerts.columns):
        return pd.DataFrame(columns=expected_columns)

    alerts["issue_datetime"] = pd.to_datetime(
        alerts["issue_datetime"], utc=True, errors="coerce"
    )
    alerts = alerts.loc[alerts["issue_datetime"].dt.date == now.date()].copy()
    messages = alerts["message"].fillna("").astype(str)
    product_ids = alerts.get("product_id", pd.Series("", index=alerts.index)).fillna("").astype(str)
    relevant = messages.str.contains(
        r"Type II Radio Emission|Type IV Radio Emission|CME|Coronal Mass Ejection",
        case=False,
        regex=True,
    ) | product_ids.isin({"TIIA", "TIVA"})
    return alerts.loc[relevant, expected_columns].sort_values("issue_datetime", ascending=False)


def latest_value(frame: pd.DataFrame, column: str) -> str:
    if frame.empty or column not in frame:
        return "No data"
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return "No data"
    return f"{values.iloc[-1]:,.1f}"


@st.fragment(run_every="60s")
def render_live_dashboard() -> None:
    now = pd.Timestamp.now(tz="UTC")
    utc_day = now.date().isoformat()
    st.caption(f"UTC date: {utc_day} · Refreshes automatically every 60 seconds")

    try:
        with st.spinner("Fetching today's space-weather data..."):
            xray = today_frame(fetch_noaa_feed(NOAA_GOES_XRAY_URL), now)
            wind = today_frame(fetch_noaa_feed(NOAA_SOLAR_WIND_URL), now)
            magnetic = today_frame(fetch_noaa_feed(NOAA_SOLAR_MAG_URL), now)
            flares = fetch_noaa_flare_events()
            flares = flares.loc[flares["beginTime"].dt.date == now.date()].copy()
            radio_alerts = today_radio_alerts(fetch_noaa_feed(NOAA_ALERTS_URL), now)
    except (requests.RequestException, ValueError) as error:
        logging.exception("Live space-weather data request failed")
        st.error(f"A live data source is temporarily unavailable: {error}")
        st.info("The page will retry automatically on its next refresh.")
        return

    long_channel = xray.loc[xray["energy"].eq("0.1-0.8nm")].copy() if "energy" in xray else xray
    if not long_channel.empty:
        long_channel["flux"] = pd.to_numeric(long_channel["flux"], errors="coerce")
        long_channel = long_channel.dropna(subset=["flux"]).sort_values("time_tag")

    stale_feeds = []
    for feed_name, frame in (
        ("GOES X-ray", long_channel),
        ("Solar wind", wind),
        ("Magnetic field", magnetic),
    ):
        if frame.empty or "time_tag" not in frame:
            stale_feeds.append(f"{feed_name}: no observations for today")
            continue
        age_minutes = (now - frame["time_tag"].max()).total_seconds() / 60
        if age_minutes > 15:
            stale_feeds.append(
                f"{feed_name}: latest observation is {age_minutes / 60:.1f} hours old"
            )
    if stale_feeds:
        st.warning("Some NOAA feeds are delayed: " + "; ".join(stale_feeds))

    latest_bz = latest_value(magnetic, "bz_gsm")
    latest_speed = latest_value(wind, "proton_speed")
    metric_cards([
        {"label": "GOES flares reported today", "value": len(flares)},
        {"label": "Radio/CME-related alerts today", "value": len(radio_alerts)},
        {"label": "Latest solar-wind speed", "value": f"{latest_speed} km/s"},
        {"label": "Latest Bz (GSM)", "value": f"{latest_bz} nT"},
    ])

    xray_column, wind_column = st.columns(2)
    with xray_column:
        graph(
            long_channel,
            x="time_tag",
            y="flux",
            title="GOES X-ray flux · 0.1–0.8 nm",
            chart_type="line",
        )
    with wind_column:
        graph(
            wind,
            x="time_tag",
            y="proton_speed",
            title="Solar-wind speed",
            chart_type="line",
        )

    magnetic_column, density_column = st.columns(2)
    with magnetic_column:
        graph(
            magnetic,
            x="time_tag",
            y="bz_gsm",
            title="Interplanetary magnetic field · Bz GSM",
            chart_type="line",
        )
    with density_column:
        graph(
            wind,
            x="time_tag",
            y="proton_density",
            title="Solar-wind proton density",
            chart_type="area",
        )

    alerts_column, flare_column = st.columns(2)
    with alerts_column:
        section_title(
            "Radio and CME-related alerts",
            "NOAA SWPC notices; Type II/IV bursts can be CME-related, not a CME catalog.",
        )
        if radio_alerts.empty:
            st.info("No matching NOAA radio-burst or CME-related alerts today.")
        else:
            data_table(radio_alerts, height=280)
    with flare_column:
        section_title("Solar flares", "NOAA GOES flare events reported today (UTC)")
        if flares.empty:
            st.info("No flare events reported today.")
        else:
            visible_columns = [
                column for column in (
                    "beginTime", "peakTime", "endTime", "classType", "xrayFlux", "satellite"
                )
                if column in flares
            ]
            data_table(flares[visible_columns], height=280)

    st.caption(f"Last rendered: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S UTC}")


def main() -> None:
    st.set_page_config(page_title="Live Space Weather", layout="wide")
    apply_dashboard_style()
    if not login_form():
        st.stop()

    Title("Live space weather", "Solar events and near-Earth measurements for today")
    render_live_dashboard()


if __name__ == "__main__":
    main()