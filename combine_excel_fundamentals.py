#2024/11/20
#Creator: Sarah You
#Objective: Combine excel spreadsheets of multiple fundamental channels
#(Asset turnover, cash conversion cycle, Debt/Equity, EBIT/Interest, return on assets)
#into a single data structure for each stock index (S&P 500, SPE 350 and TSX Composite)

#2024/11/25
#

#Import required libraries
import os, glob
import pandas as pd

# Get the base directory by moving up two levels from the current script location
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))

for dir_name in ['s&p_500', 'spe_350', 'tx_60']:
    #Define container to store worksheet outputs
    dfs = []
    # Build the path to the specific file directory
    data_dir = os.path.join(base_dir, 'company_fundamentals', dir_name)
    # Create a pattern to match Excel files in the directory
    pattern = os.path.join(data_dir, '*.xls')
    # Get a list of all Excel files matching the pattern
    excel_files = glob.glob(pattern)
    print(f"Processing directory: {data_dir}")
    print(f"Found Excel files: {excel_files}")

    #loop through each spreadsheet in each excel file and store it as a dataframe:
    for file_name in excel_files:
        whole_file = pd.ExcelFile(file_name)
        for sheet_name in whole_file.sheet_names:
            #Read the current worksheet onto a dataframe
            df = pd.read_excel(file_name, sheet_name=sheet_name)
            #Convert dataframe into long format (easier to store) and index based on Company Name and Ticker
            df_long = df.melt(
                id_vars=['Company Name','Ticker'],
                #Date (fiscal quarters) become a variable
                var_name='FQ',
                #Load fundamental metric as variable
                value_name=f"{sheet_name}"
            ) 
            df_long['FQ'] = df_long['FQ'].astype(str).str.strip()   
            # Append the long DataFrame to the list
            dfs.append(df_long)

    # Merge all DataFrames on 'Company', 'Ticker', and 'Date'
    if dfs:
        # Start with the first DataFrame
        data_merged = dfs[0]
        #Outer join each subsequent dataframe by Company Name, Ticker and fiscal quarter (basically adding columns)
        for df in dfs[1:]:
            data_merged = pd.merge(
                data_merged,
                df,
                on=['Company Name', 'Ticker', 'FQ'],
                how='outer'
            )
    else:
        print("No data frames to merge.") #Error output when no dataframes are read
    #Write 
    data_merged.to_csv(f"{dir_name}_merged_fundamentals.csv", index=False)

print("Done merging data.")
