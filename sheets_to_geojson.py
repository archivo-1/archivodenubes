import gspread
import pandas as pd
import json
import os
from gspread.exceptions import APIError
from gspread_pandas import Spread
from gspread_dataframe import set_with_dataframe
import time
from urllib.parse import urlparse
import sys
import numpy as np

def df_to_geojson(df, properties=None):
    geojson = {'type':'FeatureCollection', 'features':[]}
    
    # Define the columns that should always be at the top level of the feature, not inside properties
    top_level_special = ['geojson', 'id', 'geometry']
    
    # Define the columns that are considered "special" properties
    # They should be passed to the GeoJSON, but not treated as regular properties for dynamic inclusion
    special_property_columns = ['name', 'type', 'shape', 'colour', 'size', 'width', 'lineDash']
    
    # Identify property columns dynamically
    all_known_columns = top_level_special + special_property_columns
    property_columns = [col for col in df.columns if col not in all_known_columns]

    for _, row in df.iterrows():
        # Handle rows with missing geojson data
        if pd.isna(row.get('geojson')):
            continue

        try:
            geometry = json.loads(row['geojson'])
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Skipping row due to invalid GeoJSON: {e}")
            continue
        
        # Create the properties dictionary
        properties = {}
        for col in property_columns:
            # Check for NaN values and skip them
            if pd.notna(row[col]):
                properties[col] = row[col]
                
        # Add the special properties
        for col in special_property_columns:
            if col in row and pd.notna(row[col]):
                properties[col] = row[col]

        feature = {
            'type': 'Feature',
            'geometry': geometry,
            'properties': properties
        }

        # Add id if present
        if 'id' in row and pd.notna(row['id']):
            feature['id'] = row['id']
            
        geojson['features'].append(feature)

    return geojson

def get_sheet_id(url_or_id):
    if 'docs.google.com/spreadsheets' in url_or_id:
        try:
            parsed = urlparse(url_or_id)
            return parsed.path.split('/')[3]
        except:
            return None
    return url_or_id

def main():
    if len(sys.argv) < 5:
        print("Usage: python sheets-to-geojson.py --sheet_id <sheet_id> --geojson_path <path> --branch <branch_name>")
        sys.exit(1)

    sheet_id_arg = sys.argv.index('--sheet_id') + 1
    geojson_path_arg = sys.argv.index('--geojson_path') + 1
    branch_arg = sys.argv.index('--branch') + 1

    sheet_id = get_sheet_id(sys.argv[sheet_id_arg])
    geojson_path = sys.argv[geojson_path_arg]
    branch = sys.argv[branch_arg]

    gc = gspread.service_account(filename=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))

    try:
        sh = gc.open_by_key(sheet_id)
        ws = sh.worksheet("Sheet1") # Use your specific sheet name here
    except APIError as e:
        print(f"Error accessing Google Sheet: {e.response.text}")
        sys.exit(1)

    df = pd.DataFrame(ws.get_all_records())

    # Ensure all column names are lowercase for consistency
    df.columns = df.columns.str.lower()
    
    # Check for required geojson column
    if 'geojson' not in df.columns:
        print("Error: 'geojson' column not found in the spreadsheet.")
        sys.exit(1)

    geojson_data = df_to_geojson(df)

    with open(geojson_path, 'w') as f:
        json.dump(geojson_data, f, indent=2)

    # Use git to commit the changes and push to GitHub
    os.system(f'git config user.name "github-actions"')
    os.system(f'git config user.email "github-actions@github.com"')
    os.system(f'git checkout {branch}')
    os.system(f'git add {geojson_path}')
    os.system(f'git commit -m "Auto-update {os.path.basename(geojson_path)} from Google Sheets"')
    os.system(f'git push origin {branch}')

if __name__ == '__main__':
    main()
