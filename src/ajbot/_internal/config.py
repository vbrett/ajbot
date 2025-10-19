''' contains configuration variables
'''
from pathlib import Path

from vbrpytools.dicjsontools import load_json_file, save_json_file

from ajbot._internal.exceptions import OtherException


DATEPARSER_CONFIG = {'DATE_ORDER': 'DMY', 'DEFAULT_LANGUAGES': ["fr"]}

# Google credential needed scope (If modifying these scopes, delete the file token.json.)
AJ_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


_AJ_CONFIG_PATH = Path(".env")
_AJ_CONFIG_FILE = "ajbot"

_KEY_CREDS_DISCORD = "creds_discord"
_KEY_GUILD = "discord_guild"
_KEY_ADMIN = "discord_admin"
_KEY_CREDS_DB = "creds_db"
_KEY_FILE_ID_DB = "file_id_db"
_KEY_TABLE_EVENTS = "db_table_events"
_KEY_TABLE_ROSTER = "db_table_roster"
_KEY_TABLE_ROLE = "db_table_role"
_KEY_TABLE_EVENT_TYPE = "db_table_event_type"
_KEY_FILE_ID_PRESENCE = "file_id_presence"


class AjConfig():
    """ Context manager which handles configuration variables, retrieving them from proper sources
        and saving/updating them when needed.
    """

    def __init__(self,
                 file_path=_AJ_CONFIG_PATH / _AJ_CONFIG_FILE,
                 save_on_exit:bool=True,
                 break_if_missing:bool=False):
        """
            Initializes the AjConfig object.
        Args:
        file_path:         path to the config file.
        save_on_exit:      if True, save the config on exit.
        break_if_missing:  if True and secret not found or not valid, raise SecretException.
        """
        self._usr_creds = {}
        self._file_path = file_path
        self._save_on_exit = save_on_exit
        self._break_if_missing = break_if_missing

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def open(self):
        """ Opens the config file and loads its content.
        """
        self._usr_creds = load_json_file(self._file_path, abort_on_file_missing=self._break_if_missing)
        return self

    def close(self):
        """ Closes the config file, saving its content if needed.
        """
        if self._save_on_exit:
            save_json_file(self._usr_creds,
                        self._file_path,
                        preserve=False)

    @property
    def break_if_missing(self):
        """ Returns whether to break if a config value is missing.
        """
        return self._break_if_missing

    @property
    def discord_token(self):
        """ Returns the Discord token from config.
        """
        return self._usr_creds.get(_KEY_CREDS_DISCORD)
    @discord_token.setter
    def discord_token(self, value):
        """ Sets the Discord token in config.
        """
        self._usr_creds[_KEY_CREDS_DISCORD] = value

    @property
    def db_creds(self):
        """ Returns the Google Drive credentials from config.
        """
        return self._usr_creds.get(_KEY_CREDS_DB)
    @db_creds.setter
    def db_creds(self, value):
        """ Sets the Google Drive credentials in config.
        """
        self._usr_creds[_KEY_CREDS_DB] = value

    @property
    def file_id_db(self):
        """ Returns the Google Drive file ID for the database from config.
        """
        return self._usr_creds.get(_KEY_FILE_ID_DB)

    @property
    def db_table_events(self):
        """ Returns the database table name for events from config.
        """
        return self._usr_creds.get(_KEY_TABLE_EVENTS)

    @property
    def db_table_roster(self):
        """ Returns the database table name for roster from config.
        """
        return self._usr_creds.get(_KEY_TABLE_ROSTER)

    @property
    def db_table_role(self):
        """ Returns the database table name for roles from config.
        """
        return self._usr_creds.get(_KEY_TABLE_ROLE)

    @property
    def db_table_event_type(self):
        """ Returns the database table name for event types from config.
        """
        return self._usr_creds.get(_KEY_TABLE_EVENT_TYPE)

    @property
    def file_id_presence(self):
        """ Returns the Google Drive file ID for presence from config.
        """
        return self._usr_creds.get(_KEY_FILE_ID_PRESENCE)

    @property
    def discord_guild(self):
        """ Returns the Discord guild ID from config.
        """
        return self._usr_creds.get(_KEY_GUILD)

    @property
    def discord_admin(self):
        """ Returns the Discord admin ID from config.
        """
        return self._usr_creds.get(_KEY_ADMIN)

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
