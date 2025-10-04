""" Shows basic usage of the Drive v3 API.
"""

import io

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from ajbot._internal.exceptions import OtherException
from ajbot import credentials

class GoogleDrive:
    """ Class to interact with Google Drive API. """
    def __init__(self):
        creds = credentials.get_set_gdrive(prompt_if_present=False,
                                           break_if_missing=True)

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

if __name__ == "__main__":
    raise OtherException("This module should not be called directly.")
