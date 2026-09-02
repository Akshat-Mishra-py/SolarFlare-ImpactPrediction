import pandas as pd
import logging
import drms

class Sharp_dataset:
    def __init__(self) -> None:
        self.Client = drms.Client()
        #TODO: Split the keys into Features, Mapping and Stats in future
        self.keys = [
        # Physics & Predictive Features
        "USFLUX", "MEANGAM", "MEANGBT", "MEANGBZ", "MEANGBH", "MEANJZD", 
        "TOTUSJZ", "MEANALP", "MEANJZH", "TOTUSJH", "ABSNJZH", "SAVNCPP", 
        "MEANPOT", "TOTPOT", "MEANSHR", "SHRGT45", "R_VALUE", "GWILL",
        
        # Surface Mapping & Coordinates
        "LAT_FWT", "LON_FWT", "LAT_FWTPOS", "LON_FWTPOS", "LAT_FWTNEG", "LON_FWTNEG",
        "LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX", "CRLN_OBS", "CRLT_OBS", "DSUN_OBS", "RSUN_OBS",
        
        # Geometry & Statistics
        "AREA", "AREA_ACR", "SIZE", "SIZE_ACR", "NPIX", "MTOT", "MNET", 
        "MPOS_TOT", "MNEG_TOT", "MMEAN", "MSTDEV", "MSKEW", "MKURT",
        
        # Matching & Quality Control
        "HARPNUM", "NOAA_AR", "T_REC"
        ]
        self.series_info = self.Client.keys("hmi.sharp_720s")
        
    def fetch_data(self,start_time:str, end_time:str)->None:
        #TODO: Implement end_time so that we fetch between dates
        self.query: pd.DataFrame = self.Client.query(f"hmi.sharp_720s_nrt[][{start_time}/1d@6h]",key=self.keys) #type:ignore
        self.query["T_REC"] = pd.to_datetime(self.query["T_REC"].str.removesuffix("_TAI"), format="%Y.%m.%d_%H:%M:%S")
        self.query = self.query[self.query["NOAA_AR"]!=0]
        print(self.query)
        print(self.query.info())
        print(self.query["NOAA_AR"].describe())
if __name__ == "__main__":
    sharp_dataset = Sharp_dataset()
    sharp_dataset.fetch_data("2026.08.27","2026.08.01")
