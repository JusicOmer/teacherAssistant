import openai
import yaml
import json
import requests
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Load configuration
config = yaml.safe_load(open("config.yaml"))

# OpenAI API client
client = openai.OpenAI(api_key=config['KEYS']['openai'])

# Google Sheets API setup
SERVICE_ACCOUNT_FILE = config['GOOGLE']['service_account_file']
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=credentials)


# Function to read data from a Google Sheet
async def read_sheet(spreadsheet_id, range_name):
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    return values


# Function to write data to a Google Sheet
def write_sheet(spreadsheet_id, range_name, values):
    sheet = service.spreadsheets()
    body = {'values': values}
    result = sheet.values().update(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption="RAW",
                                   body=body).execute()
    return result


# Function to append data to a Google Sheet
def append_sheet(spreadsheet_id, range_name, values):
    sheet = service.spreadsheets()
    body = {'values': values}
    result = sheet.values().append(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption="RAW",
                                   insertDataOption="INSERT_ROWS", body=body).execute()
    return result
