import logging
import os
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

from src.dashboard.components import *
from src.data_preprocessing.donki_data_loader import Donki_dataset


NOAA_GOES_XRAY_URL = "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json"
NOAA_SOLAR_WIND_URL = "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"
NOAA_SOLAR_MAG_URL = "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"
NASA_DONKI_URL = "https://api.nasa.gov/DONKI"


@st.cache_data(ttl=60, max_entries=4, show_spinner=False)
def fetch_noaa_feed(url: str) -> list[dict]:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, max_entries=8, show_spinner=False)
def fetch_donki_events(endpoint: str, utc_day: str) -> list[dict]:
    response = requests.get(
        f"{NASA_DONKI_URL}/{endpoint}",
        params={
            "startDate": utc_day,
            "endDate": utc_day,
            "api_key": os.getenv("NASA_API") or "DEMO_KEY",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def today_frame(records: list[dict], now: pd.Timestamp) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    if frame.empty or "time_tag" not in frame.columns:
        return frame

    frame["time_tag"] = pd.to_datetime(frame["time_tag"], utc=True, errors="coerce")
    return frame.loc[frame["time_tag"].dt.date == now.date()].dropna(subset=["time_tag"])


def prepare_flares(records: list[dict]) -> pd.DataFrame:
    flares = pd.DataFrame(records)
    if flares.empty:
        return pd.DataFrame(columns=["beginTime", "peakTime", "classType", "flareType", "xrayFlux"])

    for column in ("beginTime", "peakTime", "endTime"):
        if column in flares:
            flares[column] = pd.to_datetime(flares[column], utc=True, errors="coerce")
    loader = Donki_dataset()
    flares["xrayFlux"] = flares["classType"].map(loader.get_xray_flux)
    flares["flareType"] = flares["classType"].map(loader.get_flare_type)
    if "activeRegionNum" in flares:
        flares["activeRegionNum"] = pd.to_numeric(flares["activeRegionNum"], errors="coerce")
    return flares


def prepare_cmes(records: list[dict]) -> pd.DataFrame:
    rows = []
    for event in records:
        analyses = event.get("cmeAnalyses") or []
        analysis = next((item for item in analyses if item.get("isMostAccurate")), None)
        if analysis is None and analyses:
            analysis = analyses[0]
        rows.append({
            "Start time (UTC)": event.get("startTime"),
            "Type": analysis.get("type") if analysis else None,
            "Speed (km/s)": analysis.get("speed") if analysis else None,
            "Half-angle (deg)": analysis.get("halfAngle") if analysis else None,
            "Most accurate analysis": analysis.get("isMostAccurate") if analysis else None,
            "Activity ID": event.get("activityID"),
            "Details": event.get("link"),
        })
    return pd.DataFrame(rows)


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
            flares = prepare_flares(fetch_donki_events("FLR", utc_day))
            cmes = prepare_cmes(fetch_donki_events("CME", utc_day))
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
        {"label": "CMEs reported today", "value": len(cmes)},
        {"label": "Flares reported today", "value": len(flares)},
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

    cme_column, flare_column = st.columns(2)
    with cme_column:
        section_title("Coronal mass ejections", "NASA DONKI events reported for today (UTC)")
        if cmes.empty:
            st.info("No CME events reported today.")
        else:
            data_table(cmes, height=280)
    with flare_column:
        section_title("Solar flares", "NASA DONKI events reported for today (UTC)")
        if flares.empty:
            st.info("No flare events reported today.")
        else:
            visible_columns = [
                column for column in ("beginTime", "peakTime", "classType", "xrayFlux", "activeRegionNum")
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