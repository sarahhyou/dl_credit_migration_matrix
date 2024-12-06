#Import required libraries
import os, glob
import pandas as pd
import re
from datetime import datetime


# Get the base directory by moving up two levels from the current script location
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))

file_name = 's&p-500'
# Build the path to the specific file directory
data_dir = os.path.join(base_dir, 'credit_history_reports')
# Create a pattern to match Excel files in the directory
pattern = os.path.join(data_dir, f'{file_name}.xls')
print(pattern)
# Get a list of all Excel files matching the pattern
excel_files = glob.glob(pattern)
print(f"Found Excel files: {excel_files}")
rating_migrations = []

for excel_file in excel_files:
    whole_file = pd.ExcelFile(excel_file)
    for sheet_name in whole_file.sheet_names:
        #debug print function to locate worksheets
        #print(sheet_name)

        #Read worksheet
        df = pd.read_excel(excel_file, sheet_name = sheet_name)
        #Drop first three rows
        df = df.drop([0,1,2]).reset_index(drop=True)
        df.columns = df.iloc[0]
        df.drop(df.index[0], inplace=True)
        #Drop last two rows
        df.drop(["Situation","Source"], axis=1, inplace=True)

        #Split the Headline into Current Credit Rating and Previous Credit Rating

        #Split the Headline into Current Credit Rating and Previous Credit Rating

        # Long-term ratings list (already known)
        long_term_ratings = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C', 'D', 'NR']

        # Short-term ratings list (example set; adjust as needed)
        short_term_ratings = [
            'A-1', 'A-2', 'A-3', 'B', 'C', 'D'
        ]

        # Build a pattern for long-term ratings: base + optional plus or minus
        long_term_pattern = r'(?<!\w)(?:' + '|'.join(re.escape(r) for r in long_term_ratings) + r')(?:[+-])?(?!\w)'

        # Build a pattern for short-term ratings directly from the list
        short_term_pattern = r'(?<!\w)(?:' + '|'.join(re.escape(r) for r in short_term_ratings) + r')(?!\w)'

        def extract_ratings(text):
            # Extract all long-term ratings
            lt_matches = re.findall(long_term_pattern, text)
            
            # Extract all short-term ratings
            st_matches = re.findall(short_term_pattern, text)

            # Logic to determine which rating to place in which column
            # Priority logic: 
            #  1. If we have at least one long-term rating, that becomes the New Credit Rating.
            #  2. The next available long-term rating (if any) becomes the Previous Credit Rating.
            #  3. If no second long-term rating, look at short-term ratings for the Previous Credit Rating.

            if lt_matches:
                new_rating = lt_matches[0]
                if len(lt_matches) > 1:
                    prev_rating = lt_matches[1]
                else:
                    # No second long-term rating found, use short-term if available
                    prev_rating = st_matches[0] if st_matches else 'NR'
            else:
                # No long-term rating found, try short-term
                new_rating = st_matches[0] if st_matches else 'NR'
                prev_rating = st_matches[1] if len(st_matches) > 1 else 'NR'

            return pd.Series({'New Credit Rating': new_rating, 'Previous Credit Rating': prev_rating})

        # Assuming df has the column 'Headline'
        df[['New Credit Rating', 'Previous Credit Rating']] = df['Headline'].apply(extract_ratings)

        # Create a mask that selects rows where both 'New Credit Rating' and 'Previous Credit Rating'
        # are present in long-term credit rates
        full_rates = ['AAA','AA+','AA','AA-','A+','A','A-',
              'BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-',
              'CCC+','CCC','CCC-','CC+','CC','CC-','C+','C','C-',
              'D','NR']
        
        mask = df['New Credit Rating'].isin(full_rates) & df['Previous Credit Rating'].isin(full_rates)

        # Keep only the rows that match the condition
        df = df[mask]

        #Convert dates into datetime format
        def convert_date(text):
            #Parse string into datetime context
            date_obj = datetime.strptime(text, "%b-%d-%Y %I:%M %p")
            #Format datetime object to MM/YYYY
            format_date = date_obj.strftime("%Y/%m")
            return format_date

        df['Date'] = df['Date'].apply(convert_date)

        # Drop duplicates based on Date, New Credit Rating and Previous Credit Rating
        df = df.drop_duplicates(subset=['Date','New Credit Rating','Previous Credit Rating'], keep='first')
        #Drop Event Type and Headline
        df = df.drop(['Event Type','Headline'],axis=1).reset_index(drop=True)

        #Filter for dates after 01/01/2000
        df['Date'] = pd.to_datetime(df['Date'], format='%Y/%m')
        df = df.sort_values(by='Date').reset_index(drop=True)

        #Add initial rating if first date in column is after 2000-01-01:
        initial_date = pd.to_datetime('2000-01-01')
        if df['Date'].iloc[0] > initial_date:
            initial_rating = {
                'Companies': [df['Companies'].iloc[0]],
                'Date': [initial_date],
                'New Credit Rating': ['NR'],
                'Previous Credit Rating': ['NR']
            }
            rating_history = pd.concat([pd.DataFrame(initial_rating), df], ignore_index=True)
            rating_history.sort_values(by='Date').reset_index(drop=True)
        else:
            rating_history = df

        # Create the full date range DataFrame
        date_range = pd.date_range(start='2000-01-01', end='2023-12-01', freq='MS')
        companies = df['Companies'].unique()
        # Create a DataFrame with all combinations of companies and dates
        full_df = pd.MultiIndex.from_product([companies, date_range], names=['Company', 'Date']).to_frame(index=False)
        full_df = full_df.sort_values(by='Date')
        rating_history = rating_history.rename(columns={'Date': 'Effective Date', 'Companies':'Company'})
        # Perform the 'asof' merge
        merged_df = pd.merge_asof(
            full_df,
            rating_history,
            left_on='Date',
            right_on='Effective Date',
            by='Company',
            direction='backward'
        )

        # Adjust 'Previous Credit Rating' after the last known change
        # Get the last 'Effective Date' for each company
        last_effective_date = rating_history.groupby('Company')['Effective Date'].max().reset_index()
        last_effective_date.columns = ['Company', 'Last Effective Date']

        # Merge and adjust
        merged_df = pd.merge(merged_df, last_effective_date, on='Company', how='left')
        merged_df.loc[merged_df['Date'] > merged_df['Last Effective Date'], 'Previous Credit Rating'] = merged_df['New Credit Rating']

        # Step 6: Adjust 'Previous Credit Rating' where 'Credit Rating' hasn't changed
        def adjust_previous_rating(group):
            group = group.sort_values('Date').reset_index(drop=True)
            group['Credit Rating Shift'] = group['New Credit Rating'].shift(1)
            # Initialize the first 'Credit Rating Shift' as the same as 'Credit Rating'
            group.loc[0, 'Credit Rating Shift'] = group.loc[0, 'New Credit Rating']
            group['Rating Changed'] = group['New Credit Rating'] != group['Credit Rating Shift']
            group['Previous Credit Rating'] = group.apply(
                lambda row: row['Previous Credit Rating'] if row['Rating Changed'] else row['New Credit Rating'],
                axis=1
            )
            return group

        merged_df = merged_df.groupby('Company').apply(adjust_previous_rating).reset_index(drop=True)

        # Step 8: Prepare the final DataFrame
        final_df = merged_df[['Company', 'Date', 'New Credit Rating', 'Previous Credit Rating']]

        #Collapse the information into onw row
        df_wide = final_df.pivot(index='Company', columns='Date', values='New Credit Rating')

        rating_migrations.append(df_wide)
    
    print(rating_migrations[0].index.name)
    for i, df in enumerate(rating_migrations):
        # Move the index into a column
        df.reset_index(inplace=True)
        # Now that it's a column, we can ensure it is named 'Company'
        if df.index.name is None and df.columns[0] != 'Company':
            # Rename the first column to 'Company' if needed
            df.rename(columns={df.columns[0]: 'Company'}, inplace=True)
        # Set the 'Company' column as index if desired
        df.set_index('Company', inplace=True)

    final_df = pd.concat(rating_migrations, axis=0)
    print(final_df.head(10))
    final_df.to_csv(f"{file_name}_rating_migration_matrix.csv", index=True)
    print("Done creating matrix.")