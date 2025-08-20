import pandas as pd
import gspread
import json
import argparse
import os
import requests

def get_data_from_github(repo_url, branch, file_path, github_token):
    """
    Reads the content of a GeoJSON file directly from a GitHub repository.
    """
    headers = {'Authorization': f'token {github_token}'}
    raw_url = f"https://raw.githubusercontent.com/{repo_url.split('github.com/')[1].split('.git')[0]}/{branch}/{file_path}"
    response = requests.get(raw_url, headers=headers)
    response.raise_for_status()
    return response.json()

def convert_to_dataframe(geojson_data):
    """
    Converts GeoJSON data into a pandas DataFrame.
    """
    features = geojson_data.get('features', [])
    data = []
    for feature in features:
        row = feature['properties']
        row['__geometry__'] = json.dumps(feature['geometry'])
        data.append(row)
    
    df = pd.DataFrame(data)
    geometry_col = '__geometry__'
    cols = [col for col in df.columns if col != geometry_col] + [geometry_col]
    return df[cols]

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
    except gspread.exceptions.SpreadsheetNotFound:
        raise ValueError(f"Spreadsheet '{sheet_title}' not found. Check the title and sharing permissions.")
    except gspread.exceptions.WorksheetNotFound:
        raise ValueError(f"Worksheet '{worksheet_name}' not found. Check the name.")

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
