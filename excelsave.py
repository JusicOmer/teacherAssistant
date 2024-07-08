import os
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate_drive():
    creds = None
    if os.path.exists("token_drive.json"):
        creds = Credentials.from_authorized_user_file("token_drive.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=8080)
        with open("token_drive.json", "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)

def save_drive_files_to_excel():
    service = authenticate_drive()
    try:
        # Get the list of files from Google Drive
        results = service.files().list(pageSize=1000, fields="files(id, name)").execute()
        items = results.get("files", [])
        if not items:
            print("No files found.")
            return

        # Prepare the data for the Excel sheet
        new_data = [{"Name": item["name"], "ID": item["id"]} for item in items]
        new_df = pd.DataFrame(new_data)

        # Check if the output Excel file already exists
        output_file = "google_drive_files.xlsx"
        if os.path.exists(output_file):
            # Read the existing data from the Excel file
            existing_df = pd.read_excel(output_file)

            # Merge the new data with the existing data, dropping duplicates
            combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['ID'])

            # Save the combined DataFrame to the Excel file
            combined_df.to_excel(output_file, index=False)
        else:
            # If the file doesn't exist, just save the new data
            new_df.to_excel(output_file, index=False)

        print(f"File list saved to {output_file}")
    except Exception as error:
        print(f"An error occurred: {error}")

# Call the function
save_drive_files_to_excel()
