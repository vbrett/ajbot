''' Handle storing secrets in system keyring
'''

import sys
import tkinter as tk
from tkinter import filedialog
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

import keyring
from pwinput import pwinput

from ajbot._internal.config import KEY_SERVER, KEY_USER_DISCORD, KEY_USER_DRIVE, AJ_DRIVE_SCOPES
from ajbot._internal.exceptions import SecretException

def get_set_discord(prompt_if_present = False,
                    break_if_missing = False,):
    """ Get the Discord token from the system keyring. If not found, ask for it and store it.

    Args:
        prompt_if_present: if True and secret found, ask for a new token.
                           if False and secret found, do nothing.
        break_if_missing:  if True and secret not found, raise SecretException.
    Returns:
        The Discord token, None if not found and not set.
    """
    token = keyring.get_password(KEY_SERVER, KEY_USER_DISCORD)
    if token:
        action = '' if not prompt_if_present else input("Le token d'accès à Discord est déjà défini. Voulez-vous le remplacer ? (o/n) ")
        if action.lower() != 'o':
            return token

    elif break_if_missing:
        raise SecretException("Le token d'accès à Discord n'est pas défini.")

    token = pwinput("Entrez le token d'accès à Discord : ")
    if token:
        keyring.set_password(KEY_SERVER, KEY_USER_DISCORD, token)
        return token

    if break_if_missing:
        raise SecretException("Le token d'accès à Discord n'est pas défini.")

    return None


def get_set_gdrive(prompt_if_present = False,
                   break_if_missing = False,):
    """ Get the drive token from the system keyring. If not found, ask for it and store it.
    Args:
        prompt_if_present: if True and secret found and valid, ask for new credentials.
                           if False and secret found and valid, do nothing.
        break_if_missing:  if True and secret not found or not valid, raise SecretException.
    Returns:
        The drive credential object, None if not found and not set.
    """
    # The keyring stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    creds = None
    token = keyring.get_password(KEY_SERVER, KEY_USER_DRIVE)
    if token:
        try:
            creds = Credentials.from_authorized_user_info(json.loads(token), AJ_DRIVE_SCOPES)
        except ValueError:
            pass

    # Valid credentials, prompt user whether to replace them
    if creds and creds.valid:
        action = '' if not prompt_if_present else input("Le token d'accès au drive est déjà défini et valide. Voulez-vous le remplacer ? (o/n) ")
        if action.lower() != 'o':
            return creds

    # Expired credentials, refresh them
    elif creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        keyring.set_password(KEY_SERVER, KEY_USER_DRIVE, creds.to_json())
        return creds

    # Invalid credentials, break if asked
    elif break_if_missing:
        raise SecretException("Le token d'accès au drive n'est pas défini ou n'est pas valide.")

    # Prompt for credential file
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    cred_file_path = filedialog.askopenfilename(parent = root,
                                                defaultextension=".json",
                                                title="Sélectionnez le fichier JSON contenant les info d'accès au drive",
                                                filetypes=[("Fichier JSON", "*.json"), ("Tous les fichiers", "*.*")],
                                                initialdir ="."
                                            )
    if cred_file_path:
        flow = InstalledAppFlow.from_client_secrets_file(
            cred_file_path, AJ_DRIVE_SCOPES
        )
        creds = flow.run_local_server(port=0)

        keyring.set_password(KEY_SERVER, KEY_USER_DRIVE, creds.to_json())
        return creds

    if break_if_missing:
        raise SecretException("Le token d'accès au drive n'est pas défini ou n'est pas valide.")

    return None


def _main():
    """ Simple command line interface to set the passwords in the keyring. """
    _ = get_set_discord(prompt_if_present=True, break_if_missing=False)
    _ = get_set_gdrive(prompt_if_present=True, break_if_missing=False)
    return 0


if __name__ == '__main__':
    sys.exit(_main())
