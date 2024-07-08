import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of the spreadsheet.
SPREADSHEET_ID = '1poGkKp-kwpA7vbJKBcQvbSxMf8uFnDQ4X8Xb9eIYZfc'
RANGE_NAME = 'A2:C'  # Updated range to include the email column


def authenticate_google_sheets():
    """Shows basic usage of the Sheets API."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            flow.redirect_uri = 'http://localhost:8080/'
            creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    return sheet


async def mark_homework_done(student_name):
    sheet = authenticate_google_sheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range='A2:C').execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        for i, row in enumerate(values):
            if row[0].lower() == student_name.lower():
                cell_range = f'B{i + 2}'
                sheet.values().update(spreadsheetId=SPREADSHEET_ID, range=cell_range,
                                      valueInputOption='RAW', body={'values': [['yes']]}).execute()
                print(f'Marked homework as done for {student_name}.')
                return f'Marked homework as done for {student_name}.'
        print(f'Student named {student_name} not found.')


def add_student(student_name, student_email):
    sheet = authenticate_google_sheets()
    values = [[student_name, '', student_email]]
    body = {'values': values}
    result = sheet.values().append(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME,
                                   valueInputOption='RAW', body=body).execute()
    print(f'Added new student: {student_name} with email: {student_email}')


def print_table():
    sheet = authenticate_google_sheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range='A1:C').execute()  # Note: A1:C to include headers
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        for row in values:
            print('\t'.join(row))


def get_student_email(student_name):
    sheet = authenticate_google_sheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range='A2:C').execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        for row in values:
            if row[0].lower() == student_name.lower():
                print(f"The email for {student_name} is {row[2]}")
                return row[2]
        print(f'Student named {student_name} not found.')
        return None

#
# if __name__ == '__main__':
#     while True:
#         print("Options:")
#         print("1. Mark homework as done")
#         print("2. Add a new student")
#         print("3. Print the table content")
#         print("4. Get student's email")
#         print("5. Exit")
#         choice = input("Enter your choice: ")
#
#         if choice == '1':
#             student_name = input("Enter the student's name: ")
#             mark_homework_done(student_name)
#         elif choice == '2':
#             student_name = input("Enter the new student's name: ")
#             student_email = input("Enter the new student's email: ")
#             add_student(student_name, student_email)
#         elif choice == '3':
#             print_table()
#         elif choice == '4':
#             student_name = input("Enter the student's name: ")
#             get_student_email(student_name)
#         elif choice == '5':
#             break
#         else:
#             print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
