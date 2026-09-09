from donki_data_loader import Donki_dataset
from sharp_data_loader import Sharp_dataset
import numpy as np
import pandas as pd

class TrainingMergedDataset:
    def __init__(self, start_date:str, end_date:str) -> None:
        #This will get the data to be converted into training ready data.
        self.donkiDataset = Donki_dataset()
        self.flareData = self.donkiDataset.fetch_flares(start_date, end_date)

        self.sharpDataset = Sharp_dataset()
        self.sharpData = self.sharpDataset.fetch_data(start_date, end_date)

    def convert_event_timeseries(self, df:pd.DataFrame, start_time:str, end_time:str, interval:str):
        startTime = pd.to_datetime(start_time)
        endTime = pd.to_datetime(end_time)
        range = pd.date_range(startTime, endTime, interval)

