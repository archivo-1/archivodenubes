import pandas as pd
import gspread
import json
import argparse
import os
from github import Github

def get_data_from_google_sheet(sheet_title, worksheet_name, credentials_path):
    """
    Authenticates with Google and fetches data from a specified sheet and worksheet.
    """
    try:
        gc = gspread.service_account(filename=credentials_path)
        sh = gc.open(sheet_title)
        worksheet = sh.worksheet(worksheet_name)
        df = pd.DataFrame(worksheet.get_all_records())
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        raise ValueError(f"Spreadsheet '{sheet_title}' not found. Check the title and sharing permissions.")
    except gspread.exceptions.WorksheetNotFound:
        raise ValueError(f"Worksheet '{worksheet_name}' not found. Check the name.")

def create_geojson(df, geometry_col):
    """
    Converts a pandas DataFrame into a GeoJSON FeatureCollection.
    """
    features = []
    for _, row in df.iterrows():
        properties = {k: v for k, v in row.to_dict().items() if k != geometry_col}

        if row[geometry_col] not in [None, '']:
            try:
                geometry_data = json.loads(row[geometry_col])
                feature = {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": geometry_data
                }
                features.append(feature)
            except json.JSONDecodeError:
                print(f"Skipping row with invalid geometry data: {row[geometry_col]}")
        
    return {
        "type": "FeatureCollection",
        "features": features
    }

def update_github(repo_url, branch, file_path, new_content, github_token):
    """
    Authenticates with GitHub and pushes the new file content to the repository.
    """
    g = Github(github_token)
    repo_name = repo_url.split('github.com/')[1]
    repo = g.get_repo(repo_name)
    
    try:
        contents = repo.get_contents(file_path, ref=branch)
        repo.update_file(contents.path, f"Update {file_path}", new_content, contents.sha, branch=branch)
        print(f"Successfully updated {file_path} on branch '{branch}'.")
    except Exception as e:
        print(f"Failed to update file. Attempting to create a new file...")
        repo.create_file(file_path, f"Create {file_path}", new_content, branch=branch)
        print(f"Successfully created a new file at {file_path} on branch '{branch}'.")

def main():
    parser = argparse.ArgumentParser(description='Update GeoJSON files from Google Sheets.')
    parser.add_argument('--sheet_title', required=True, help='The exact title of the Google Sheet.')
    parser.add_argument('--geojson_path', required=True, help='The path to the GeoJSON file in the GitHub repo.')
    parser.add_argument('--branch', required=True, help='The branch to push changes to.')
    args = parser.parse_args()

    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    github_token = os.environ.get('GITHUB_TOKEN')
    repo_url = 'https://github.com/archivo-1/archivodenubes'
    
    if not credentials_path or not github_token:
        raise ValueError("Environment variables GOOGLE_APPLICATION_CREDENTIALS and GITHUB_TOKEN must be set.")

    df = get_data_from_google_sheet(args.sheet_title, 'Sheet1', credentials_path)
    geojson_data = create_geojson(df, '__geometry__')
    
    update_github(repo_url, args.branch, args.geojson_path, json.dumps(geojson_data, indent=2), github_token)

if __name__ == '__main__':
    main()
