from collections.abc import Sequence
from datetime import date
import hmac
import os
import time
from typing import Literal, NotRequired, TypedDict

import pandas as pd
import streamlit as st


class Metric(TypedDict):
    label: str
    value: str | int | float
    delta: NotRequired[str | int | float]
    help: NotRequired[str]


ChartType = Literal["line", "bar", "area", "scatter"]


def _configured_credentials() -> tuple[str, str]:
    try:
        auth_settings = st.secrets.get("auth", {})
    except FileNotFoundError:
        auth_settings = {}

    username = os.environ.get("DASHBOARD_USERNAME") or auth_settings.get("username", "")
    password = os.environ.get("DASHBOARD_PASSWORD") or auth_settings.get("password", "")
    return username, password


def login_form() -> bool:
    """Show a session-based login form using environment variables or Streamlit secrets."""
    if st.session_state.get("authenticated", False):
        with st.sidebar:
            st.caption(f"Signed in as {st.session_state.get('dashboard_username', 'user')}")
            if st.button("Log out", use_container_width=True):
                st.session_state["authenticated"] = False
                st.session_state.pop("dashboard_username", None)
                st.rerun()
        return True

    expected_username, expected_password = _configured_credentials()
    st.title("Solar activity dashboard")
    if not expected_username or not expected_password:
        st.error("Dashboard login is not configured. Set DASHBOARD_USERNAME and DASHBOARD_PASSWORD.")
        return False

    with st.form("dashboard_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

    if submitted:
        if not rate_limit("login_attempt", interval_seconds=2):
            st.warning("Please wait a moment before trying to sign in again.")
        else:
            username_matches = hmac.compare_digest(username, expected_username)
            password_matches = hmac.compare_digest(password, expected_password)
            if username_matches and password_matches:
                st.session_state["authenticated"] = True
                st.session_state["dashboard_username"] = username
                st.rerun()
            st.error("Invalid username or password.")
    return False


def date_range_filter(
    start_date: date,
    end_date: date,
    *,
    key: str = "dashboard_date_range",
) -> tuple[date, date, bool]:
    """Render an apply-to-update date range form and return its values and submit state."""
    with st.form(key):
        start_column, end_column = st.columns(2)
        with start_column:
            selected_start = st.date_input("Start date", value=start_date)
        with end_column:
            selected_end = st.date_input("End date", value=end_date)
        submitted = st.form_submit_button("Apply date range", type="primary")

    if submitted and selected_start > selected_end:
        st.error("Start date must be on or before the end date.")
        submitted = False
    return selected_start, selected_end, submitted


def rate_limit(key: str, interval_seconds: int = 5) -> bool:
    """Allow one action per Streamlit session during the configured interval."""
    now = time.monotonic()
    last_action = st.session_state.get(f"rate_limit_{key}")
    if last_action is not None and now - last_action < interval_seconds:
        return False
    st.session_state[f"rate_limit_{key}"] = now
    return True


def apply_dashboard_style() -> None:
    """Apply a restrained, consistent style to the current Streamlit page."""
    st.markdown(
        """
        <style>
            .block-container { padding-top: 2rem; padding-bottom: 3rem; }
            [data-testid="stMetric"] {
                padding: 0.25rem 0;
            }
            [data-testid="stMetricLabel"] p {
                color: #52616b;
                font-size: 0.82rem;
                font-weight: 600;
            }
            [data-testid="stMetricValue"] {
                color: #17324d;
                font-size: 1.8rem;
                font-weight: 700;
            }
            [data-testid="stCaptionContainer"] { color: #64748b; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def Title(title: str, subtitle: str | None = None) -> None:
    """Render a page title and optional supporting description."""
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def section_title(title: str, description: str | None = None) -> None:
    st.subheader(title)
    if description:
        st.caption(description)


def metric_cards(metrics: Sequence[Metric]) -> None:
    """Render summary metrics in responsive rows of up to four columns."""
    for start in range(0, len(metrics), 4):
        row = metrics[start:start + 4]
        columns = st.columns(len(row))
        for column, metric in zip(columns, row):
            with column:
                with st.container(border=True):
                    st.metric(
                        label=metric["label"],
                        value=metric["value"],
                        delta=metric.get("delta"),
                        help=metric.get("help"),
                    )


def graph(
    data: pd.DataFrame | None = None,
    *,
    x: str | None = None,
    y: str | Sequence[str] | None = None,
    title: str | None = None,
    chart_type: ChartType = "line",
    height: int = 360,
) -> None:
    """Render a built-in Streamlit chart from a dataframe."""
    if data is None or data.empty:
        st.info("No data available to display.")
        return

    chart_functions = {
        "line": st.line_chart,
        "bar": st.bar_chart,
        "area": st.area_chart,
        "scatter": st.scatter_chart,
    }
    if chart_type not in chart_functions:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    with st.container(border=True):
        if title:
            st.subheader(title)
        chart_functions[chart_type](
            data,
            x=x,
            y=y,
            height=height,
            width="stretch",
        )


def data_table(
    data: pd.DataFrame,
    *,
    title: str | None = None,
    height: int = 360,
) -> None:
    """Display a dataframe in a consistently framed, scrollable table."""
    with st.container(border=True):
        if title:
            st.subheader(title)
        if data.empty:
            st.info("No data available to display.")
            return
        st.dataframe(data, height=height, width="stretch")