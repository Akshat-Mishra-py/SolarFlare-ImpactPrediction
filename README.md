# ProjectExhibition1

## Run the dashboard

Configure login credentials using environment variables:

```powershell
$env:DASHBOARD_USERNAME = "your-username"
$env:DASHBOARD_PASSWORD = "your-password"
uv run streamlit run .\main.py
```

Alternatively, create `.streamlit/secrets.toml` with:

```toml
[auth]
username = "your-username"
password = "your-password"
```

Do not commit credentials or the secrets file. Flare events come from NOAA's GOES X-ray catalog, which provides a rolling seven-day window and does not include active-region IDs or a full CME catalog. The live page uses NOAA SWPC alerts for radio-burst and CME-related notices. NOAA requests are cached to avoid unnecessary polling. Sign-in attempts are limited to one per session every two seconds, and date-range requests to one per signed-in session every five seconds. These in-app limits are lightweight session-level controls, not a substitute for a shared production rate limiter.
