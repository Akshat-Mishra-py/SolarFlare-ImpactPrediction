# Solar Activity Dashboard

An authenticated Streamlit application for monitoring solar activity, exploring recent GOES flare observations, and demonstrating a short-term flare outlook. The dashboard combines live NOAA Space Weather Prediction Center (SWPC) feeds with a supplied historical flare dataset.

The project is designed as an exhibition-ready scientific dashboard: it emphasizes readable metrics, UTC-aware timestamps, transparent data provenance, and clear boundaries between live observations and simulated predictions.

## Capabilities

### Live space weather

The **Live Space Weather** page refreshes automatically every 60 seconds and presents today's UTC observations:

- GOES X-ray flux for the 0.1-0.8 nm channel
- Solar-wind speed and proton density
- Interplanetary magnetic-field Bz in GSM coordinates
- GOES flare events reported today
- NOAA radio-burst and CME-related alerts
- Staleness warnings when a feed has not updated recently

### Flare observations

The main dashboard loads NOAA's seven-day GOES flare catalog and supports a selectable UTC date range within that rolling window. It provides:

- Flare count, peak class, peak X-ray flux, and active-region summary metrics
- X-ray peak flux over time
- Daily flare counts
- Flare-class distribution
- Most-active-region chart when region data is available
- A tabular view of the source observations

### Flare predictions

The **Flare Predictions** page creates a 24-hour, hourly demo forecast from `FlareData_2026-01-01_2026-09-29.json`. The forecast uses historical hourly frequencies, a smoothed event rate, and historical class frequencies to produce:

- Hourly flare probability
- Likely flare class if an event occurs
- A/B/C/M/X severity bands
- Local-time and UTC forecast timestamps
- A scrollable 24-hour forecast table

This is an empirical demonstration model, not a trained or operational forecasting system. Its purpose is to show how historical observations can be translated into an interpretable forecast interface.

## Quick start

### Requirements

- Windows, macOS, or Linux
- Python 3.11
- `uv` for environment and dependency management
- A NOAA SWPC network connection for live pages

Install the project dependencies:

```powershell
uv sync
```

Configure dashboard credentials with environment variables:

```powershell
$env:DASHBOARD_USERNAME = "your-username"
$env:DASHBOARD_PASSWORD = "your-password"
```

Start the application:

```powershell
uv run streamlit run .\main.py
```

Streamlit will open the dashboard in a browser. Sign in with the configured credentials, then use the page selector in the sidebar to move between the live, analysis, and prediction views.

## Configuration

Credentials can also be supplied through `.streamlit/secrets.toml`:

```toml
[auth]
username = "your-username"
password = "your-password"
```

Environment variables take precedence over Streamlit secrets. The repository ignores `secrets.*` and `.env` files; do not commit real credentials or API keys.

The optional `.example.env` file documents variables used by the experimental data-acquisition path:

- `NASA_API` for NASA DONKI access
- `JSOC_MAIL` for JSOC/DRMS access

Those credentials are not required to run the live dashboard or the supplied demo forecast.

## Data sources

| Source | Use in the application | Refresh or scope |
| --- | --- | --- |
| NOAA SWPC GOES X-ray feed | Today's X-ray measurements | Cached for 60 seconds |
| NOAA SWPC real-time solar-wind feed | Proton speed and density | Cached for 60 seconds |
| NOAA SWPC real-time magnetic feed | Bz GSM measurements | Cached for 60 seconds |
| NOAA SWPC alerts feed | Radio-burst and CME-related notices | Cached for 60 seconds |
| NOAA SWPC GOES flare catalog | Seven-day flare observations | Cached for 300 seconds |
| `FlareData_2026-01-01_2026-09-29.json` | Historical input for the demo forecast | Loaded locally and cached |
| NASA DONKI and JSOC SHARP | Experimental training-data preparation | Used by data-preprocessing modules, not by the main dashboard flow |

All displayed live times are normalized to UTC. The prediction page additionally shows the same forecast window in the machine's local timezone.

## Architecture

```text
main.py
	-> NOAADataLoader
	-> dashboard components
	-> seven-day flare analysis

pages/1_Live_Space_Weather.py
	-> NOAA SWPC JSON feeds
	-> live telemetry and alert tables

pages/2_Flare_Predictions.py
	-> local historical JSON
	-> generate_demo_forecast()
	-> 24-hour prediction view

src/data_preprocessing/
	-> NOAA, DONKI, and SHARP data access
	-> event-to-timeseries conversion
	-> overlapping training-window preparation
```

Shared presentation and interaction behavior lives in `src/dashboard/components.py`, including login, rate limiting, date filtering, metric cards, charts, and data tables.

## Caching and request controls

Streamlit data caching reduces repeated NOAA requests:

- Live telemetry and alert feeds: 60-second cache
- NOAA flare catalog: 300-second cache
- Historical prediction input: cached for the session

The application also applies lightweight per-session controls:

- Login attempts: one every two seconds
- Flare date-range refreshes: one every five seconds

These controls protect the interactive session from accidental rapid requests. They are not a replacement for authentication middleware, shared rate limiting, monitoring, or a production deployment gateway.

## Important limitations

- NOAA's GOES flare endpoint exposes a rolling seven-day window, so older date ranges are not available through the main dashboard.
- The GOES flare feed does not provide a complete CME catalog. CME-related content on the live page is based on filtered NOAA alerts and is labeled accordingly.
- Active-region identifiers may be unavailable in the NOAA GOES feed; the dashboard reports that limitation rather than inventing values.
- The prediction view is a reproducible empirical demo and should not be used for operational decisions.
- The login is a lightweight Streamlit session gate. It is suitable for an exhibition or local demonstration, not as a complete production identity system.
- NOAA feeds are external services. Network outages, delayed observations, schema changes, and API availability can affect the live pages.

## Project layout

```text
.
├── main.py                              # Main flare-analysis dashboard
├── pages/
│   ├── 1_Live_Space_Weather.py         # Live telemetry and alerts
│   └── 2_Flare_Predictions.py          # 24-hour demo forecast
├── src/dashboard/
│   ├── components.py                    # Shared UI, login, charts, tables
│   └── flare_prediction.py              # Forecast generation logic
├── src/data_preprocessing/
│   ├── noaa_data_loader.py              # NOAA flare and alert access
│   ├── donki_data_loader.py             # NASA DONKI flare access
│   ├── sharp_data_loader.py             # JSOC SHARP access
│   └── training_dataset_builder.py     # Event-series and window preparation
├── FlareData_2026-01-01_2026-09-29.json # Supplied forecast history
├── .streamlit/config.toml               # Theme and chart colors
├── pyproject.toml                       # Package metadata and dependencies
└── uv.lock                              # Locked dependency versions
```

## Development checks

Run a syntax check across the Python source:

```powershell
uv run python -m compileall main.py pages src
```

Run the application locally:

```powershell
uv run streamlit run .\main.py
```

When testing the live pages, confirm that the displayed UTC date, latest-observation timestamps, staleness notices, and empty-state messages behave correctly when a feed is delayed or unavailable.

## Presentation

The repository includes [Solar_Activity_Dashboard_Presentation.pptx](Solar_Activity_Dashboard_Presentation.pptx), a presentation-ready overview of the problem, dashboard pages, data sources, prediction method, architecture, and limitations. The original `solar_flare_project.pptx` is retained as a prior project artifact.

The deck can be regenerated after content changes with:

```powershell
uv run python .\scripts\create_presentation.py
```
