import pandas as pd
import logging
import drms

class Sharp_dataset:
    def __init__(self) -> None:
        self.Client = drms.Client()
        self.query = self.Client.query("hmi.sharp_cea_720s",key="T_REC")
        print(self.query)
if __name__ == "__main__":
    sharp_dataset = Sharp_dataset()
    
