import os, glob
import pandas as pd

path = r".\month_avg_stock"

def stack_data(path):
    allFiles = glob.glob(f"{path}\*.xlsx")
    dfs = [
        pd.read_excel(file, sheet_name='Screening').assign(
            source=os.path.basename(file), dir=os.path.basename(path)
        ) for file in allFiles 
    ]
    return pd.concat(dfs, ignore_index=True, axis=1)

df = stack_data(path)
df.sample(10)
