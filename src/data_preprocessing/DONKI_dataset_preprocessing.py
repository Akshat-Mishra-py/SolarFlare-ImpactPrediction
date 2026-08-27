import requests
import pandas as pd
import logging
from os import getenv

class Donki_dataset:
    def __init__(self):
        self.url =  "https://api.nasa.gov/DONKI"

        
    def fetch_flares(self, start_date:str, end_date:str) -> None:
        ''' Fetches the data for class of flares
            Args : 
            start_date (str): yyyy-mm-dd
            end_date (str): yyyy-mm-dd'''
        self.flare_params = {"startDate" : start_date, "endDate" : end_date, "api_key": getenv("NASA_API")} 

        logging.info(f"Fetching Flare Dataset: start_date = {start_date} end_date = {end_date}")
        response = requests.get(self.url+"/FLR", self.flare_params, timeout=30)
        try:
            response.raise_for_status()
        except Exception as e:
            logging.critical(f"Error: Failed to fetch flares dataset, Exception -> {e}")

        events = response.json()
        df = pd.DataFrame(events)
        print(df.head(15)[['flrID', "classType"]])
        
if __name__ == "__main__":
    donki_data = Donki_dataset()
    donki_data.fetch_flares("2026-08-01", "2026-08-27")