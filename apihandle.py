import base64
import io
import mimetypes
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# OAuth2 scopes required for Gmail and Drive API
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive'
]


def authenticate_drive():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=8080)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def authenticate_gmail():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=8081)  # Use a different port for Gmail API authentication
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def list_files():
    service = authenticate_drive()
    try:
        results = service.files().list(pageSize=100, fields="files(id, name)").execute()
        items = results.get("files", [])
        if not items:
            return "No files found."
        file_list = [{"id": item["id"], "name": item["name"]} for item in items]
        return file_list
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def delete_file(fileid):
    service = authenticate_drive()
    try:
        service.files().delete(fileId=fileid).execute()
        return {"message": "File deleted successfully"}
    except HttpError as error:
        print(f"An error occurred: {error}")
        return {"message": "Failed to delete file"}


def list_unread_emails():
    service = authenticate_gmail()
    email_list = []
    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=10).execute()
        messages = results.get('messages', [])
        if not messages:
            return "No unread messages found."

        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            headers = msg['payload']['headers']
            sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown')
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')

            try:
                if msg['payload']['mimeType'] == 'text/plain':
                    text = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
                else:
                    parts = [part for part in msg['payload'].get('parts', []) if part['mimeType'] == 'text/plain']
                    if parts:
                        text_part = parts[0]
                        text = base64.urlsafe_b64decode(text_part['body']['data']).decode('utf-8')
                    else:
                        text = "No text content available."
            except Exception as e:
                text = f"Error retrieving content: {e}"

            email_list.append({
                'sender': sender,
                'subject': subject,
                'text': text
            })

    except HttpError as error:
        print(f"An error occurred: {error}")

    return email_list


def get_attachments_from_email(email_id, store_dir):
    service = authenticate_gmail()
    try:
        message = service.users().messages().get(userId='me', id=email_id).execute()
        for part in message['payload']['parts']:
            if part['filename']:
                attachment_id = part['body'].get('attachmentId')
                attachment = service.users().messages().attachments().get(userId='me', messageId=message['id'],
                                                                          id=attachment_id).execute()
                file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
                file_path = os.path.join(store_dir, part['filename'])
                with open(file_path, 'wb') as f:
                    f.write(file_data)
        return f"Attachments saved to {store_dir}"
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def download_file_from_drive(file_id):
    service = authenticate_drive()
    try:
        # Get the file metadata to retrieve the original filename and MIME type
        file_metadata = service.files().get(fileId=file_id, fields='name, mimeType').execute()
        print(file_metadata.get('name'))
        file_name = file_metadata.get('name')
        mime_type = file_metadata.get('mimeType')
        file_path = os.path.join(os.getcwd(), file_name)

        print(f"Downloading file: {file_name} (MIME type: {mime_type}) to path: {file_path}")

        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")
        print(f"File downloaded to {file_path}.")
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None, None
    return file_path, mime_type


def send_email_with_attachment(to, subject, message_text, file_path, mime_type):
    service = authenticate_gmail()
    try:
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject

        msg = MIMEText(message_text)
        message.attach(msg)

        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(file_path)

        print(f"Attaching file: {file_path} with MIME type: {mime_type}")

        part = MIMEBase(*mime_type.split('/'))
        with open(file_path, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)

        filename = os.path.basename(file_path)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        print(f'Content-Disposition header: {part.get("Content-Disposition")}')
        message.attach(part)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw}

        message = service.users().messages().send(userId='me', body=body).execute()
        print(f"Message sent: {message['id']}")
    except HttpError as error:
        print(f"An error occurred: {error}")