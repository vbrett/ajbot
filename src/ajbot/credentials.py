''' Handle storing secrets in config file.
'''

import sys
from platform import system
from pathlib import Path
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from pwinput import pwinput

from ajbot._internal.config import AJ_DRIVE_SCOPES, AjConfig
from ajbot._internal.exceptions import CredsException


def get_set_discord(aj_config:AjConfig,
                    prompt_if_present = False,):
    """ Get the Discord token from the conf file. If not found, ask for it and store it.

    Args:
        aj_config: AjConfig object to use to store the token.
        prompt_if_present: if True and secret found, ask for a new token.
                           if False and secret found, do nothing.
    Returns:
        The Discord token, None if not found and not set.
    """
    token = aj_config.discord_token

    if token:
        action = '' if not prompt_if_present else input("Le token d'accès à Discord est déjà défini. Voulez-vous le remplacer ? (o/n) ")
        if action.lower() != 'o':
            return token

    elif aj_config.break_if_missing:
        raise CredsException("Le token d'accès à Discord n'est pas défini.")

    token = pwinput("Entrez le token d'accès à Discord : ")
    if token:
        aj_config.discord_token = token
        return token

    if aj_config.break_if_missing:
        raise CredsException("Le token d'accès à Discord n'est pas défini.")

    return None


def get_set_gdrive(aj_config:AjConfig,
                   prompt_if_present = False,):
    """ Get the drive token from the conf file. If not found, ask for it and store it.
    Args:
        aj_config: AjConfig object to use to store the credentials information
        prompt_if_present: if True and secret found and valid, ask for new credentials.
                           if False and secret found and valid, do nothing.
    Returns:
        The drive credential object, None if not found and not set.
    """
    # The conf file stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    creds = None

    if aj_config.db_creds:
        try:
            creds = Credentials.from_authorized_user_info(aj_config.db_creds, AJ_DRIVE_SCOPES)
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
        aj_config.db_creds = json.loads(creds.to_json())
        return creds

    # Invalid credentials, break if asked
    elif aj_config.break_if_missing:
        raise CredsException("Le token d'accès au drive n'est pas défini ou n'est pas valide.")

    # Prompt for credential file
    if system() != 'Windows':
        cred_file_path = input("Entrez le chemin du fichier JSON contenant les info d'accès au drive : ")

    else:
        import tkinter as tk            #pylint: disable=import-outside-toplevel    #this is done because it only is supported in windows system
        from tkinter import filedialog  #pylint: disable=import-outside-toplevel    #this is done because it only is supported in windows system
        root = tk.Tk()   #pylint: disable=possibly-used-before-assignment #this code is only ran in windows system
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        cred_file_path = filedialog.askopenfilename(parent = root,   #pylint: disable=possibly-used-before-assignment #this code is only ran in windows system
                                                    defaultextension=".json",
                                                    title="Sélectionnez le fichier JSON contenant les info d'accès au drive",
                                                    filetypes=[("Fichier JSON", "*.json"), ("Tous les fichiers", "*.*")],
                                                    initialdir ="."
                                                )

    if Path(cred_file_path).is_file():
        flow = InstalledAppFlow.from_client_secrets_file(
            cred_file_path, AJ_DRIVE_SCOPES
        )
        creds = flow.run_local_server(port=0)

        aj_config.db_creds = json.loads(creds.to_json())
        return creds

    if aj_config.break_if_missing:
        raise CredsException("Le token d'accès au drive n'est pas défini ou n'est pas valide.")

    return None


def _main():
    """ Simple command line interface to set or update the passwords & credentials in config file. """
    with AjConfig(break_if_missing=False, save_on_exit=True) as aj_config:
        _ = get_set_discord(aj_config, prompt_if_present=True)
        _ = get_set_gdrive(aj_config, prompt_if_present=True)
    return 0


if __name__ == '__main__':
    sys.exit(_main())
