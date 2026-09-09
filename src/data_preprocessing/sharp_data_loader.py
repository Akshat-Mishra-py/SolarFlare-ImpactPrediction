import pandas as pd
import logging
import drms

class Sharp_dataset:
    def __init__(self) -> None:
        self.Client = drms.Client()
        self.features = ["USFLUX", "MEANGAM", "MEANGBT", "MEANGBZ", "MEANGBH", "MEANJZD", 
                "TOTUSJZ", "MEANALP", "MEANJZH", "TOTUSJH", "ABSNJZH", "SAVNCPP", 
                "MEANPOT", "TOTPOT", "MEANSHR", "SHRGT45", "R_VALUE", "GWILL",]

        self.surface_mapping = ["LAT_FWT", "LON_FWT", "LAT_FWTPOS", "LON_FWTPOS", "LAT_FWTNEG", 
        "LON_FWTNEG","LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX", "CRLN_OBS", "CRLT_OBS", "DSUN_OBS",
        "RSUN_OBS"] 

        self.keys = ["AREA", "AREA_ACR", "SIZE", "SIZE_ACR", "NPIX", "MTOT", "MNET", 
        "MPOS_TOT", "MNEG_TOT", "MMEAN", "MSTDEV", "MSKEW", "MKURT",
        # Matching & Quality Control
        "HARPNUM", "NOAA_AR", "T_REC"
        ] + self.features + self.surface_mapping 
        self.series_info = self.Client.keys("hmi.sharp_720s")
        
    def fetch_data(self,start_time:str, end_time:str, interval:str="1h") -> None:
        start_time = start_time.replace("-", ".")
        end_time = start_time.replace("-", ".")
        self.query: pd.DataFrame = self.Client.query(f"hmi.sharp_720s_nrt[][{start_time}-{end_time}@{interval}]",key=self.keys) #type:ignore
        self.query["T_REC"] = pd.to_datetime(self.query["T_REC"].str.removesuffix("_TAI"), format="%Y.%m.%d_%H:%M:%S")
        self.query = self.query[self.query["NOAA_AR"]!=0] #Only take features where activeRegions are present
        grps = []
        for arr, grp in self.query.groupby("NOAA_AR"):
            grps.append(grp.sort_values('T_REC'))
        print(grps)
        
if __name__ == "__main__":
    sharp_dataset = Sharp_dataset()
    sharp_dataset.fetch_data("2026-09-01","2026-09-03","1h")
    