import pandas as pd
import gspread
import json
import argparse
import os
import requests
import numpy as np
import re
from gspread.utils import a1_to_rowcol, rowcol_to_a1

def get_data_from_github(repo_url, branch, file_path, github_token):
    """
    Reads the content of a GeoJSON file directly from a GitHub repository.
    """
    headers = {'Authorization': f'token {github_token}'}
    raw_url = f"https://raw.githubusercontent.com/{repo_url.split('github.com/')[1].split('.git')[0]}/{branch}/{file_path}"
    response = requests.get(raw_url, headers=headers)
    response.raise_for_status()
    return response.json()

def clean_data(df):
    """
    Cleans the DataFrame by converting non-scalar values to strings
    and replacing NaN/inf with empty strings.
    """
    df = df.replace([np.inf, -np.inf], np.nan)
    
    for col in df.columns:
        df[col] = df[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)
    
    return df.fillna('')

def convert_to_dataframe(geojson_data):
    """
    Converts GeoJSON data into a pandas DataFrame.
    """
    features = geojson_data.get('features', [])
    data = []
    
    if not features:
        return pd.DataFrame()

    # Consolidate all possible property keys across all features
    all_keys = set()
    for feature in features:
        all_keys.update(feature.get('properties', {}).keys())

    for feature in features:
        row = feature.get('properties', {})
        row['__geometry__'] = json.dumps(feature.get('geometry', {}))
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Define a custom column order: 'name', 'type', then the rest alphabetically
    fixed_cols = ['name', 'type']
    remaining_cols = sorted([k for k in all_keys if k not in fixed_cols])
    
    geometry_col = '__geometry__'
    cols = fixed_cols + remaining_cols + [geometry_col]
    df = df.reindex(columns=cols, fill_value=None)
    
    df = clean_data(df)
    
    return df

def update_google_sheet(df, sheet_title, worksheet_name, credentials_path):
    """
    Updates a Google Sheet with data from a pandas DataFrame and applies formatting
    using a single batch update request to avoid API rate limits.
    """
    try:
        gc = gspread.service_account(filename=credentials_path)
        sh = gc.open(sheet_title)
        worksheet = sh.worksheet(worksheet_name)
        
        # Prepare the data for a single update
        all_values = [df.columns.values.tolist()] + df.values.tolist()
        worksheet.clear()
        worksheet.update(all_values)
        
        requests_body = []
        
        # 1. Bold the header row
        header_range = f'A1:{rowcol_to_a1(1, df.shape[1])}'
        requests_body.append({
            'repeatCell': {
                'range': {
                    'sheetId': worksheet.id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {
                            'bold': True
                        }
                    }
                },
                'fields': 'userEnteredFormat.textFormat.bold'
            }
        })
        
        # 2. Collect all hex code coloring requests
        hex_code_pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
        
        for row_index, row in enumerate(all_values):
            for col_index, value in enumerate(row):
                if isinstance(value, str) and hex_code_pattern.match(value):
                    requests_body.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': worksheet.id,
                                'startRowIndex': row_index,
                                'endRowIndex': row_index + 1,
                                'startColumnIndex': col_index,
                                'endColumnIndex': col_index + 1
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': {
                                        'red': int(value[1:3], 16) / 255.0,
                                        'green': int(value[3:5], 16) / 255.0,
                                        'blue': int(value[5:7], 16) / 255.0
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat.backgroundColor'
                        }
                    })

        # Send all formatting requests in one batch
        if requests_body:
            worksheet.client.batch_update(sh.id, {'requests': requests_body})
        
        print(f"Successfully updated and formatted sheet '{sheet_title}'.")
    except gspread.exceptions.WorksheetNotFound:
        raise ValueError(f"Worksheet '{worksheet_name}' not found. Check the name.")
    except gspread.exceptions.APIError as e:
        print(f"Google Sheets API Error: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Update Google Sheets from GeoJSON files.')
    parser.add_argument('--sheet_title', required=True, help='The exact title of the Google Sheet.')
    parser.add_argument('--geojson_path', required=True, help='The path to the GeoJSON file in the GitHub repo.')
    parser.add_argument('--branch', required=True, help='The branch to read the GeoJSON from.')
    args = parser.parse_args()

    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    github_token = os.environ.get('GITHUB_TOKEN')
    repo_url = 'https://github.com/archivo-1/archivodenubes'
    
    if not credentials_path or not github_token:
        raise ValueError("Environment variables GOOGLE_APPLICATION_CREDENTIALS and GITHUB_TOKEN must be set.")

    geojson_data = get_data_from_github(repo_url, args.branch, args.geojson_path, github_token)
    df = convert_to_dataframe(geojson_data)
    
    update_google_sheet(df, args.sheet_title, 'Sheet1', credentials_path)

if __name__ == '__main__':
    main()
