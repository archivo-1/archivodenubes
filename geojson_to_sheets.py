import pandas as pd
import gspread
import json
import argparse
import os
import requests
import numpy as np

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
    
    # Reindex to ensure all columns are present across all features
    geometry_col = '__geometry__'
    cols = sorted(list(all_keys)) + [geometry_col]
    df = df.reindex(columns=cols, fill_value=None)
    
    df = clean_data(df)
    
    return df

def update_google_sheet(df, sheet_title, worksheet_name, credentials_path):
    """
    Updates a Google Sheet with data from a pandas DataFrame.
    """
    try:
        gc = gspread.service_account(filename=credentials_path)
        sh = gc.open(sheet_title)
        worksheet = sh.worksheet(worksheet_name)
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        print(f"Successfully updated sheet '{sheet_title}'.")
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
