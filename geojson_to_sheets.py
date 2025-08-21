import json
import gspread
import pandas as pd
import sys
import os
from gspread.exceptions import APIError
from gspread_pandas import Spread
from gspread_dataframe import set_with_dataframe
import numpy as np

def get_sheet_id(url_or_id):
    if 'docs.google.com/spreadsheets' in url_or_id:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url_or_id)
            return parsed.path.split('/')[3]
        except:
            return None
    return url_or_id

def main():
    if len(sys.argv) < 5:
        print("Usage: python geojson_to_sheets.py --geojson_path <path> --sheet_id <sheet_id>")
        sys.exit(1)

    geojson_path_arg = sys.argv.index('--geojson_path') + 1
    sheet_id_arg = sys.argv.index('--sheet_id') + 1

    geojson_path = sys.argv[geojson_path_arg]
    sheet_id = get_sheet_id(sys.argv[sheet_id_arg])
    
    # We now get the credentials from the environment variable directly
    gc = gspread.service_account(filename=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))

    try:
        sh = gc.open_by_key(sheet_id)
        ws = sh.worksheet("Sheet1")
    except APIError as e:
        print(f"Error accessing Google Sheet: {e.response.text}")
        sys.exit(1)

    with open(geojson_path, 'r') as f:
        geojson_data = json.load(f)

    if 'features' not in geojson_data:
        print("Invalid GeoJSON file: 'features' key not found.")
        sys.exit(1)

    # Prepare DataFrame columns
    df_data = []
    
    # Identify all possible properties
    all_properties = set()
    for feature in geojson_data['features']:
        if 'properties' in feature and feature['properties'] is not None:
            all_properties.update(feature['properties'].keys())

    # Build the list of columns for the dataframe
    column_order = ['id', 'geojson']
    for prop in sorted(list(all_properties)):
        if prop not in ['id', 'geojson']:
            column_order.append(prop)

    for feature in geojson_data['features']:
        row_dict = {}
        row_dict['id'] = feature.get('id', '')

        if 'geometry' in feature and feature['geometry'] is not None:
            # Check for coordinates to prevent errors on empty geometries
            if 'coordinates' in feature['geometry']:
                row_dict['geojson'] = json.dumps({
                    'type': feature['geometry']['type'],
                    'coordinates': feature['geometry']['coordinates']
                }).replace(' ', '')
            else:
                row_dict['geojson'] = ''
        else:
            row_dict['geojson'] = ''
        
        # Add all properties dynamically
        for prop, value in feature.get('properties', {}).items():
            row_dict[prop] = value

        df_data.append(row_dict)

    df = pd.DataFrame(df_data, columns=column_order)
    df = df.applymap(lambda x: str(x) if isinstance(x, (dict, list, np.ndarray)) else x)

    # Set the new DataFrame to the Google Sheet
    ws.clear()
    set_with_dataframe(ws, df, include_index=False)
    print("Google Sheet updated successfully.")

if __name__ == '__main__':
    main()
