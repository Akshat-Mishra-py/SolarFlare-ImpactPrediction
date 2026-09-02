import requests
import pandas as pd
import logging
from os import getenv
from json import loads

class Donki_dataset:
    def __init__(self):
        self.url =  "https://api.nasa.gov/DONKI"

        
    def fetch_flares(self, start_date:str, end_date:str) -> pd.DataFrame:
        ''' Fetches the data for class of flares
            Args : 
            start_date (str): yyyy-mm-dd
            end_date (str): yyyy-mm-dd'''
        self.flare_params = {"startDate" : start_date, "endDate" : end_date, "api_key": getenv("NASA_API")} 

        logging.info(f"Fetching Flare Dataset: start_date = {start_date} end_date = {end_date}")

        response=self.stream_data(self.url+"/FLR", self.flare_params)
        events = loads(response)
        df = pd.DataFrame(events)
        df["activeRegionNum"] = df["activeRegionNum"].dropna().astype(int)
        print(df.head())
        return df
    
    def stream_data(self, url:str, params:dict, timeout:int = 10) -> bytes:
        with requests.get(url, params, stream=True,timeout=timeout) as r:
            print("Fetching Flare Data")
            total_size = int(r.headers.get("content-length", 0))
            print(f"Total Size: {total_size/(1024*1024):.2f} MB")
            response=b""
            chunk_size = 30
            downloaded_bytes = 0
            try:
                r.raise_for_status()
            except Exception as e:
                logging.critical(f"Error: Failed to fetch flares dataset, Exception -> {e}")
                
            for chunk in r.iter_content(chunk_size):
                if chunk:
                    response+=chunk
                    downloaded_bytes += len(chunk) 
                    status_text = f"📥 Downloaded: {downloaded_bytes / 1024:.1f} KB"
                    print(f"\r\033[K{status_text}", end="", flush=True)
        return response

if __name__ == "__main__":
    donki_data = Donki_dataset()
    data = donki_data.fetch_flares("2026-01-01", "2026-08-27")
    print(data[data["activeRegionNum"]==14519, "activeRegionNum"])