import pandas as pd
import gspread
import json
import argparse
import os
import requests
import re
import sys
import numpy as np

def get_data_from_github(repo_url, branch, file_path, github_token):
    """
    Fetches the raw content of a GeoJSON file from a GitHub repository.
    """
    raw_url = f"https://raw.githubusercontent.com/{repo_url}/{branch}/{file_path}"
    headers = {'Authorization': f'token {github_token}'}
    
    try:
        response = requests.get(raw_url, headers=headers)
        response.raise_for_status()
        geojson_data = response.json()
        print(f"Successfully fetched '{file_path}' from GitHub.")
        return geojson_data
    except requests.exceptions.HTTPError as e:
        raise Exception(f"Failed to retrieve GeoJSON file from GitHub. Check repo name, branch, and file path. Error: {e}")
    except json.JSONDecodeError:
        raise Exception("Failed to decode JSON. The file might be corrupted or empty.")

def convert_to_dataframe(geojson_data):
    """
    Converts a GeoJSON FeatureCollection to a pandas DataFrame.
    """
    features = geojson_data.get('features', [])
    
    if not features:
        raise ValueError("GeoJSON file is empty or missing 'features'.")

    data = []
    
    for feature in features:
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        row = properties
        row['__geometry__'] = json.dumps(geometry)
        data.append(row)

    df = pd.DataFrame(data)
    
    # Ensure all columns are present, even if some features are missing a property
    all_keys = set()
    for feature in features:
        all_keys.update(feature.get('properties', {}).keys())
    
    for key in all_keys:
        if key not in df.columns:
            df[key] = None
    
    # Reorder columns to have __geometry__ at the end
    cols = [col for col in df.columns if col != '__geometry__'] + ['__geometry__']
    df = df[cols]
    
    # Clean the dataframe by replacing NaN and inf with a value that can be written to a sheet
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.fillna('')
    
    # Convert lists and dictionaries within properties to JSON strings
    for col in df.columns:
        if col != '__geometry__':
            df[col] = df[col].apply(
                lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x
            )
    
    return df

def update_google_sheet(df, sheet_id, worksheet_name, credentials_path):
    """
    Updates a Google Sheet with data from a pandas DataFrame and applies formatting
    using a single batch update request to avoid API rate limits.
    """
    try:
        gc = gspread.service_account(filename=credentials_path)
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(worksheet_name)
        
        all_values = [df.columns.values.tolist()] + df.values.tolist()
        worksheet.clear()
        worksheet.update(all_values)
        
        requests_body = []
        
        requests_body.append({
            'updateSheetProperties': {
                'properties': {
                    'sheetId': worksheet.id,
                    'gridProperties': {
                        'frozenRowCount': 1
                    }
                },
                'fields': 'gridProperties.frozenRowCount'
            }
        })

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
        
        num_columns = df.shape[1]
        if num_columns > 1:
            requests_body.append({
                'repeatCell': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': worksheet.row_count,
                        'endColumnIndex': num_columns - 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'wrapStrategy': 'CLIP'
                        }
                    },
                    'fields': 'userEnteredFormat.wrapStrategy'
                }
            })

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

        if requests_body:
            worksheet.client.batch_update(sh.id, {'requests': requests_body})
        
        print(f"Successfully updated and formatted sheet with ID '{sheet_id}'.")
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
    parser.add_argument('--sheet_id', required=True, help='The unique ID of the Google Sheet.')
    parser.add_argument('--geojson_path', required=True, help='The path to the GeoJSON file in the GitHub repo.')
    parser.add_argument('--branch', required=True, help='The branch to read the GeoJSON from.')
    args = parser.parse_args()

    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    github_token = os.environ.get('GITHUB_TOKEN')
    repo_url = os.environ.get('GITHUB_REPOSITORY')
    
    if not credentials_path or not github_token:
        raise ValueError("Environment variables GOOGLE_APPLICATION_CREDENTIALS and GITHUB_TOKEN must be set.")

    geojson_data = get_data_from_github(repo_url, args.branch, args.geojson_path, github_token)
    df = convert_to_dataframe(geojson_data)
    
    update_google_sheet(df, args.sheet_id, 'Sheet1', credentials_path)

if __name__ == '__main__':
    main()
