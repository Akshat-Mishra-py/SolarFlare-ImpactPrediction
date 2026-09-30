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

Do not commit credentials or the secrets file. The dashboard caches DONKI results for five minutes, limits sign-in attempts to one per session every two seconds, and limits new date-range requests to one per signed-in session every five seconds. These in-app limits are lightweight session-level controls, not a substitute for a shared production rate limiter.
