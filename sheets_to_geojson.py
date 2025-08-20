import pandas as pd
import gspread
import json
import argparse
import os
import requests
import sys
import numpy as np
import re

def get_data_from_google_sheet(sheet_id, worksheet_name, credentials_path):
    """
    Reads data from a Google Sheet using its ID and returns it as a pandas DataFrame.
    """
    try:
        gc = gspread.service_account(filename=credentials_path)
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(worksheet_name)
        
        all_values = worksheet.get_all_values()
        
        if not all_values:
            raise ValueError("The worksheet is empty. Please check the sheet and its contents.")
        
        header = all_values[0]
        data = all_values[1:]
        
        df = pd.DataFrame(data, columns=header)
        
        if df.empty:
            raise ValueError("The DataFrame is empty. This might be due to a problem with the header row or no data rows.")
        
        print(f"Successfully read data from sheet with ID '{sheet_id}'.")
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        raise ValueError(f"Spreadsheet with ID '{sheet_id}' not not found. Check the ID and sharing permissions.")
    except gspread.exceptions.WorksheetNotFound:
        raise ValueError(f"Worksheet '{worksheet_name}' not found. Check the name.")
    except Exception as e:
        print(f"An unexpected error occurred while reading the sheet: {e}", file=sys.stderr)
        raise

def clean_data(df):
    """
    Cleans the DataFrame by ensuring all text is valid UTF-8 and replacing
    NaN/inf with empty strings.
    """
    # Replace NaN/inf values with empty strings
    df = df.replace([np.inf, -np.inf, np.nan], '')
    
    # Ensure all text is UTF-8 encoded
    for col in df.columns:
        df[col] = df[col].astype(str).apply(lambda x: x.encode('utf-8', 'ignore').decode('utf-8'))
    
    return df

def convert_to_geojson(df):
    """
    Converts a pandas DataFrame back into a GeoJSON structure.
    """
    # Clean the data before conversion
    df = clean_data(df)

    if '__geometry__' not in df.columns:
        raise ValueError("The dataframe is missing the '__geometry__' column. Cannot convert to GeoJSON.")

    features = []
    
    # Split the DataFrame into properties and geometry
    prop_df = df.drop(columns=['__geometry__'])
    
    # Iterate over rows to build each GeoJSON feature
    for index, row in prop_df.iterrows():
        properties = row.to_dict()
        
        # Parse the geometry string back to a dictionary
        geometry_string = df.loc[index, '__geometry__']
        
        # Handle empty geometry strings
        if not geometry_string:
            geometry = None
        else:
            try:
                geometry = json.loads(geometry_string)
            except json.JSONDecodeError:
                print(f"Skipping row {index} due to invalid JSON in '__geometry__' column.")
                continue

        feature = {
            "type": "Feature",
            "properties": properties,
            "geometry": geometry
        }
        features.append(feature)
        
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

    # Get the current file's SHA to update it
    response = requests.get(api_url, headers=headers)
    
    sha = None
    if response.status_code == 200:
        sha = response.json().get("sha")
    elif response.status_code != 404:
        raise Exception(f"Failed to get file SHA: {response.text}")
    
    # Prepare the payload for the update/create
    payload = {
        "message": f"Update {file_path} from Google Sheets",
        "content": new_content.encode("utf-8").hex(),
        "branch": branch,
    }
    
    if sha:
        payload["sha"] = sha

    # Make the API call to update or create the file
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
