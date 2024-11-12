#2024/11/11
#Creator: Sarah You
#Objective: write function that combines data from separate excel spreadsheets specifically in the `month_avg_stock` folder into a single dataframe

#Import required libraries
import os, glob
import pandas as pd

# Get the base directory by moving up two levels from the current script location
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))


for dir_name in ['S&P 500', 'SPE 350', 'TSX']:
    # Build the path to the specific file directory
    data_dir = os.path.join(base_dir, 'month_avg_stock', dir_name)
    # Create a pattern to match Excel files in the directory
    pattern = os.path.join(data_dir, '*.xls')
    # Get a list of all Excel files matching the pattern
    excel_files = glob.glob(pattern)
    print(f"Processing directory: {data_dir}")
    print(f"Found Excel files: {excel_files}")
    # Initialize an empty list to store DataFrames
    dataframes = []

    # Loop through each file and read it into a DataFrame
    for file in excel_files:
        df = pd.read_excel(file)
        dataframes.append(df)
    # Combine all DataFrames into a single DataFrame
    dataframes[1] = dataframes[1].drop('Company Name', axis=1)
    combined_df = dataframes[0].join(dataframes[1].set_index('ExchangeTicker'), on='ExchangeTicker')
    # Save to CSV
    combined_df.to_csv(f'combined_data_{dir_name}.csv', index=False)

print("Done combining data.")