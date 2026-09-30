import re

import pandas as pd
import requests


NOAA_FLARE_EVENTS_URL = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json"
NOAA_ALERTS_URL = "https://services.swpc.noaa.gov/products/alerts.json"


class NOAADataLoader:
    def _fetch_json_list(self, url: str, timeout: int = 15) -> list[dict]:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        records = response.json()
        if not isinstance(records, list):
            raise ValueError(f"Expected a JSON list from {url}")
        return records

    def fetch_flare_events(self) -> pd.DataFrame:
        records = self._fetch_json_list(NOAA_FLARE_EVENTS_URL)
        flares = pd.DataFrame(records).rename(columns={
            "begin_time": "beginTime",
            "max_time": "peakTime",
            "end_time": "endTime",
            "begin_class": "beginClassType",
            "max_class": "classType",
            "end_class": "endClassType",
            "max_xrlong": "xrayFlux",
        })
        expected_columns = [
            "beginTime", "peakTime", "endTime", "beginClassType", "classType",
            "endClassType", "xrayFlux", "satellite", "activeRegionNum", "flareType",
        ]
        if flares.empty:
            empty_flares = pd.DataFrame(columns=expected_columns)
            for column in ("beginTime", "peakTime", "endTime"):
                empty_flares[column] = pd.to_datetime(empty_flares[column], utc=True)
            empty_flares["xrayFlux"] = pd.Series(dtype="float64")
            empty_flares["activeRegionNum"] = pd.Series(dtype="Int64")
            return empty_flares

        for column in ("beginTime", "peakTime", "endTime"):
            if column in flares:
                flares[column] = pd.to_datetime(flares[column], utc=True, errors="coerce")
        flares["classType"] = flares["classType"].astype("string").str.upper()
        valid_classes = flares["classType"].str.match(r"^[ABCMX]\d+(?:\.\d+)?$", na=False)
        flares = flares.loc[valid_classes].copy()
        flares["flareType"] = flares["classType"].str.extract(r"^([ABCMX])", flags=re.IGNORECASE)
        flares["xrayFlux"] = pd.to_numeric(flares["xrayFlux"], errors="coerce")
        flares["activeRegionNum"] = pd.Series(pd.NA, index=flares.index, dtype="Int64")

        for column in expected_columns:
            if column not in flares:
                flares[column] = pd.NA
        return flares

    def fetch_alerts(self) -> pd.DataFrame:
        return pd.DataFrame(self._fetch_json_list(NOAA_ALERTS_URL))