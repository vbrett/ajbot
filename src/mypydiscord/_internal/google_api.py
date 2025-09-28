""" Shows basic usage of the Drive v3 API.
"""

import io
from pathlib import Path
from importlib.resources import files

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from mypydiscord import secret_resources

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]

TOKEN = files(secret_resources).joinpath("token.json")
CREDENTIALS = files(secret_resources).joinpath("credentials.json")

class GoogleDrive:
    """ Class to interact with Google Drive API. """
    def __init__(self):
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if Path.exists(TOKEN):
            creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS, SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(TOKEN, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

        try:
            self.service = build("drive", "v3", credentials=creds)

        except HttpError as error:
            # TODO(developer) - Handle errors from drive API.
            print(f"An error occurred: {error}")

    def get_file(self, file_id):
        """Get a file's metadata.
        Args:
            file_id: ID of the file to retrieve metadata for.
        Returns:
            File metadata if successful, None otherwise.
        """
        request = self.service.files().get_media(fileId=file_id) # pylint: disable=no-member    #file is actually a member of service.files()
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}.")

        return file
