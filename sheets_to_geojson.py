import pandas as pd
import gspread
import json
import argparse
import os
import requests
import sys
import numpy as np
import re
import base64

def get_data_from_google_sheet(sheet_id, worksheet_name, credentials_path):
    """
    Reads data from a Google Sheet using its ID and returns it as a pandas DataFrame.
    """
    try:
        gc = gspread.service_account(filename=credentials_path)
        sh = gc.open_by_key(sheet_id)
        
        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"Warning: Worksheet '{worksheet_name}' not found. Returning empty DataFrame.")
            return pd.DataFrame()
            
        all_values = worksheet.get_all_values()
        
        if not all_values or not any(row for row in all_values):
            print(f"Warning: Worksheet '{worksheet_name}' is empty.")
            return pd.DataFrame()
        
        header = all_values[0]
        data = all_values[1:]
        
        df = pd.DataFrame(data, columns=header)
        
        if df.empty:
            print(f"Warning: DataFrame is empty for worksheet '{worksheet_name}'. This may be due to only a header row existing.")
            return pd.DataFrame()
        
        print(f"Successfully read data from sheet with ID '{sheet_id}'.")
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        raise ValueError(f"Spreadsheet with ID '{sheet_id}' not found. Check the ID and sharing permissions.")
    except Exception as e:
        print(f"An unexpected error occurred while reading the sheet: {e}", file=sys.stderr)
        raise

def clean_data(df):
    """
    Cleans the DataFrame by ensuring all text is valid UTF-8 and replacing
    NaN/inf with empty strings.
    """
    df = df.replace([np.inf, -np.inf, np.nan], '')
    for col in df.columns:
        df[col] = df[col].astype(str).apply(lambda x: x.encode('utf-8', 'ignore').decode('utf-8'))
    return df

def convert_to_geojson(df):
    """
    Converts a pandas DataFrame back into a GeoJSON structure.
    """
    if df.empty:
        return {"type": "FeatureCollection", "features": []}

    df = clean_data(df)

    if '__geometry__' not in df.columns:
        raise ValueError("The dataframe is missing the '__geometry__' column. Cannot convert to GeoJSON.")

    features = []
    
    for index, row in df.iterrows():
        try:
            properties_raw = row.drop('__geometry__').to_dict()
            
            geometry_string = str(row['__geometry__'])
            
            properties = {}
            for key, value in properties_raw.items():
                if pd.isna(value) or value == '':
                    properties[key] = None
                else:
                    try:
                        properties[key] = json.loads(str(value))
                    except (json.JSONDecodeError, TypeError):
                        properties[key] = str(value)

            geometry = None
            if geometry_string and not pd.isna(geometry_string):
                try:
                    geometry = json.loads(geometry_string)
                except (json.JSONDecodeError, TypeError):
                    print(f"Warning: Corrupt geometry data found in row {index}. Setting geometry to None.")
                    geometry = None

            feature = {
                "type": "Feature",
                "properties": properties,
                "geometry": geometry
            }
            features.append(feature)
        except Exception as e:
            print(f"Error processing row {index}. Skipping this row. Error: {e}")
            continue
        
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return geojson_data


def update_github_file(repo_url, file_path, new_content, branch, github_token):
    """
    Updates a file in a GitHub repository with new content using a direct API call.
    """
    api_url = f"https://api.github.com/repos/{repo_url}/contents/{file_path}"
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.com.v3+json"
    }

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        sha = response.json().get("sha")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            sha = None
        else:
            raise Exception(f"Failed to get file SHA: {e.response.text}")
    
    payload = {
        "message": f"Update {file_path} from Google Sheets",
        "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
        "branch": branch,
    }
    
    if sha:
        payload["sha"] = sha

    response = requests.put(api_url, json=payload, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"Successfully updated file '{file_path}' on branch '{branch}'.")
    else:
        raise Exception(f"Failed to update file '{file_path}': {response.text}")

def main():
    parser = argparse.ArgumentParser(description='Update GeoJSON files from Google Sheets.')
    parser.add_argument('--sheet_id', required=True, help='The unique ID of the Google Sheet.')
    parser.add_argument('--geojson_path', required=True, help='The path to the GeoJSON file in the GitHub repo.')
    parser.add_argument('--branch', required=True, help='The branch to read the GeoJSON from.')
    args = parser.parse_args()

    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    github_token = os.environ.get('GITHUB_TOKEN')
    repo_url = os.environ.get('GITHUB_REPOSITORY')
    
    if not credentials_path or not github_token:
        raise ValueError("Environment variables GOOGLE_APPLICATION_CREDENTIALS and GITHUB_TOKEN must be set.")

    df = get_data_from_google_sheet(args.sheet_id, 'Sheet1', credentials_path)

    geojson_data = convert_to_geojson(df)
    new_content = json.dumps(geojson_data, indent=2)

    update_github_file(repo_url, args.geojson_path, new_content, args.branch, github_token)

if __name__ == '__main__':
    main()
