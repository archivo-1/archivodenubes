import pandas as pd
import gspread
import json
import argparse
import os
from github import Github

def get_data_from_google_sheet(sheet_title, worksheet_name, credentials_path):
    """
    Reads data from a Google Sheet and returns it as a pandas DataFrame.
    """
    try:
        gc = gspread.service_account(filename=credentials_path)
        sh = gc.open(sheet_title)
        worksheet = sh.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        print(f"Successfully read data from sheet '{sheet_title}'.")
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        raise ValueError(f"Spreadsheet '{sheet_title}' not found. Check the title and sharing permissions.")
    except gspread.exceptions.WorksheetNotFound:
        raise ValueError(f"Worksheet '{worksheet_name}' not found. Check the name.")

def convert_to_geojson(df):
    """
    Converts a pandas DataFrame back into a GeoJSON structure.
    """
    features = []
    
    # Split the DataFrame into properties and geometry
    prop_df = df.drop(columns=['__geometry__'])
    
    # Iterate over rows to build each GeoJSON feature
    for index, row in prop_df.iterrows():
        properties = row.to_dict()
        
        # Parse the geometry string back to a dictionary
        geometry_string = df.loc[index, '__geometry__']
        geometry = json.loads(geometry_string)
        
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

def update_github_file(repo_name, file_path, new_content, branch, github_token):
    """
    Updates a file in a GitHub repository with new content.
    """
    g = Github(github_token)
    repo = g.get_user().get_repo(repo_name)
    
    try:
        contents = repo.get_contents(file_path, ref=branch)
        repo.update_file(
            contents.path,
            f"Update {file_path} from Google Sheets",
            new_content,
            contents.sha,
            branch=branch
        )
        print(f"Successfully updated file '{file_path}' on branch '{branch}'.")
    except Exception as e:
        print(f"Could not update file '{file_path}': {e}")
        repo.create_file(
            file_path,
            f"Create {file_path} from Google Sheets",
            new_content,
            branch=branch
        )
        print(f"Created new file '{file_path}' on branch '{branch}'.")

def main():
    parser = argparse.ArgumentParser(description='Update GeoJSON files from Google Sheets.')
    parser.add_argument('--sheet_title', required=True, help='The exact title of the Google Sheet.')
    parser.add_argument('--geojson_path', required=True, help='The path to the GeoJSON file in the GitHub repo.')
    parser.add_argument('--branch', required=True, help='The branch to read the GeoJSON from.')
    args = parser.parse_args()

    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    github_token = os.environ.get('GITHUB_TOKEN')
    repo_url = os.environ.get('GITHUB_REPOSITORY', 'archivo-1/archivodenubes')
    repo_name = repo_url.split('/')[-1]
    
    if not credentials_path or not github_token:
        raise ValueError("Environment variables GOOGLE_APPLICATION_CREDENTIALS and GITHUB_TOKEN must be set.")

    # Get data from Google Sheets
    df = get_data_from_google_sheet(args.sheet_title, 'Sheet1', credentials_path)

    # Convert to GeoJSON
    geojson_data = convert_to_geojson(df)
    new_content = json.dumps(geojson_data, indent=2)

    # Update the GeoJSON file on GitHub
    update_github_file(repo_name, args.geojson_path, new_content, args.branch, github_token)

if __name__ == '__main__':
    main()
