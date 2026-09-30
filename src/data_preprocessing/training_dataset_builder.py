from donki_data_loader import Donki_dataset
from sharp_data_loader import Sharp_dataset
import numpy as np
import pandas as pd

#TODO: use weighted loss functions instead of ctgans
class TrainingMergedDataset:
    def __init__(self, start_date:str, end_date:str) -> None:
        #This will get the data to be converted into training ready data.
        self.start_date = start_date
        self.end_date= end_date
        self.donkiDataset = Donki_dataset()
        self.flareData = self.donkiDataset.fetch_flares(start_date, end_date)

        self.sharpDataset = Sharp_dataset()
        # self.sharpData, self.noaa_numbers = self.sharpDataset.fetch_data(start_date, end_date)

    def convert_event_timeseries(
        self,
        df:pd.DataFrame|None,
        start_time:str,
        end_time:str,
        interval:str
    ) -> pd.DataFrame:
        """Convert DONKI flare events into a time-by-NOAA x-ray flux table."""
        start_timestamp = pd.to_datetime(start_time, utc=True).tz_localize(None)
        end_timestamp = pd.to_datetime(end_time, utc=True).tz_localize(None)
        timestamps = pd.date_range(start_timestamp, end_timestamp, freq=interval)
        event_series = pd.DataFrame(index=timestamps)
        event_series.index.name = "T_REC"

        required_columns = {"beginTime", "activeRegionNum", "xrayFlux"}
        if timestamps.empty or df is None or df.empty or not required_columns.issubset(df.columns):
            return event_series

        events = df.loc[:, ["beginTime", "activeRegionNum", "xrayFlux"]].copy()
        events["beginTime"] = pd.to_datetime(events["beginTime"], utc=True).dt.tz_localize(None)
        events["xrayFlux"] = pd.to_numeric(events["xrayFlux"], errors="coerce")
        events = events.dropna(subset=["beginTime", "activeRegionNum", "xrayFlux"])
        events["activeRegionNum"] = events["activeRegionNum"].astype(int)
        events = events[
            events["activeRegionNum"].ne(0)
            & events["beginTime"].between(timestamps[0], timestamps[-1])
        ]

        for noaa_number, region_events in events.groupby("activeRegionNum"):
            flux = region_events.set_index("beginTime")["xrayFlux"].sort_index()
            binned_flux = flux.resample(interval, origin=timestamps[0]).max()
            binned_flux = binned_flux.reindex(timestamps, fill_value=0)
            event_series[int(str(noaa_number))] = binned_flux.fillna(0)

        return event_series

    def slicing(
        self,
        noaa_grp:list[pd.DataFrame],
        window_length:str = "24h",
        stride:str = "1h"
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Create overlapping [time, features] windows independently per NOAA region.

        Returns the input batch, NOAA number for each sample, and each window's
        start timestamp. Transpose an individual sample for [features, time].
        """
        window_duration = pd.Timedelta(window_length)
        stride_duration = pd.Timedelta(stride)
        if window_duration <= pd.Timedelta(0) or stride_duration <= pd.Timedelta(0):
            raise ValueError("window_length and stride must be positive durations")

        feature_columns = (
            list(self.sharpDataset.features)
            if not noaa_grp
            else [
                column for column in self.sharpDataset.features
                if any(column in group.columns for group in noaa_grp)
            ]
        )
        if not feature_columns:
            raise ValueError("No SHARP feature columns are present in the NOAA groups")

        windows: list[np.ndarray] = []
        sample_noaa: list[int] = []
        window_starts: list[np.datetime64] = []

        for group in noaa_grp:
            if "T_REC" not in group or "NOAA_AR" not in group:
                raise ValueError("Each NOAA group must contain T_REC and NOAA_AR columns")

            region = group.dropna(subset=["T_REC"]).copy()
            if region.empty:
                continue
            region["T_REC"] = pd.to_datetime(region["T_REC"])
            region = region.sort_values("T_REC").drop_duplicates("T_REC", keep="last")
            region = region.set_index("T_REC")[feature_columns]
            region = region.apply(pd.to_numeric, errors="coerce")

            if len(region.index) < 2:
                continue
            differences = region.index.to_series().diff().dropna()
            cadence = pd.Timedelta(
                differences.sort_values().iloc[len(differences) // 2]
            )
            if pd.isna(cadence) or cadence <= pd.Timedelta(0):
                continue

            cadence_seconds = cadence.total_seconds()
            window_steps = max(1, round(window_duration.total_seconds() / cadence_seconds))
            stride_steps = max(1, round(stride_duration.total_seconds() / cadence_seconds))
            regular_index = pd.date_range(region.index.min(), region.index.max(), freq=cadence)
            region = region.reindex(regular_index)
            region = region.interpolate(method="time", limit=2, limit_area="inside")

            noaa_number = int(group["NOAA_AR"].dropna().iloc[0])
            for start in range(0, len(region) - window_steps + 1, stride_steps):
                sample = region.iloc[start:start + window_steps]
                values = sample.to_numpy(dtype=np.float32)
                if not np.isfinite(values).all():
                    continue
                windows.append(values)
                sample_noaa.append(noaa_number)
                window_starts.append(sample.index[0].to_datetime64())

        if windows:
            input_batch = np.stack(windows)
        else:
            window_steps = max(1, int(round(window_duration / pd.Timedelta("1h"))))
            input_batch = np.empty((0, window_steps, len(feature_columns)), dtype=np.float32)

        return (
            input_batch,
            np.asarray(sample_noaa, dtype=np.int64),
            np.asarray(window_starts, dtype="datetime64[ns]")
        )
                
if __name__ == "__main__":
    start_date = "2026-01-01"
    end_date = "2026-09-29"
    training = TrainingMergedDataset(start_date,end_date)
    t = training.convert_event_timeseries(training.flareData, training.start_date, training.end_date , "12min")