''' contains configuration variables
'''
from pathlib import Path
from urllib.parse import quote_plus
from dataclasses import dataclass

from vbrpytools.dicjsontools import load_json_file, save_json_file

from ajbot._internal.exceptions import OtherException

_AJ_ID_PREFIX = "AJ-"

_AJ_CONFIG_PATH = Path(".env")
_AJ_CONFIG_FILE = "ajbot"

_KEY_CREDS = "creds"

_KEY_DISCORD = "discord"
_KEY_GUILD = "guild"
_KEY_OWNER = "owner"
_KEY_ROLE_MANAGER = "role_manager"
_KEY_ROLE_MEMBER = "role_member"

_KEY_DB = "db"
_KEY_DB_HOST = "host"
_KEY_DB_PORT = "port"
_KEY_DB_CREDS_USR = "user"
_KEY_DB_CREDS_PWD = "password"
_KEY_DB_NAME = "db_name"
_KEY_DB_ECHO = "db_echo"

@dataclass
class FormatTypes():
    """ supported format types
    """
    RESTRICTED = ''     # since f'{xxx}' is equivalent to format(xxx, ''), defining RESTRICTED to '' enforces f'' string woth no format to be same as restricted
    FULLSIMPLE = 'full_simple'
    FULLCOMPLETE = 'full_complete'


class AjConfig():
    """ Context manager which handles configuration variables, retrieving them from proper sources
        and saving/updating them when needed.
    """

    def __init__(self,
                 file_path=_AJ_CONFIG_PATH / _AJ_CONFIG_FILE,
                 save_on_exit:bool=False):
        """
            Initializes the AjConfig object.
        Args:
        file_path:         path to the config file.
        save_on_exit:      if True, save the config on exit.
        """
        self._config_dict = {}
        self._file_path = file_path
        self._save_on_exit = save_on_exit

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def open(self):
        """ Opens the config file and loads its content.
        """
        self._config_dict = load_json_file(self._file_path, abort_on_file_missing=True)
        return self

    def close(self):
        """ Closes the config file, saving its content if needed.
        """
        self.save()

    def save(self, force_save:bool=False):
        """ Saves the config file.
        """
        if self._save_on_exit or force_save:
            save_json_file(self._config_dict,
                        self._file_path,
                        preserve=False)

    @property
    def discord_token(self):
        """ Returns the Discord token from config.
        """
        return self._config_dict[_KEY_DISCORD].get(_KEY_CREDS)
    @discord_token.setter
    def discord_token(self, value):
        """ Sets the Discord token in config.
        """
        self._config_dict[_KEY_DISCORD][_KEY_CREDS] = value

    @property
    def discord_guild(self):
        """ Returns the Discord guild ID from config.
        """
        return self._config_dict[_KEY_DISCORD].get(_KEY_GUILD)

    @property
    def discord_bot_owner(self):
        """ Returns the Discord bot owner ID from config.
        """
        return self._config_dict[_KEY_DISCORD].get(_KEY_OWNER)

    @property
    def discord_role_manager(self):
        """ Returns the Discord role manager IDs from config.
        """
        return self._config_dict[_KEY_DISCORD].get(_KEY_ROLE_MANAGER)

    @property
    def discord_role_member(self):
        """ Returns the Discord role member IDs from config.
        """
        return self._config_dict[_KEY_DISCORD].get(_KEY_ROLE_MEMBER)

    @property
    def db_creds(self):
        """ Returns the DB credentials from config as user, password tuple.
        """
        return self._config_dict[_KEY_DB].get(_KEY_CREDS)
    @db_creds.setter
    def db_creds(self, value):
        """ Sets the DB credentials in config.
        """
        self._config_dict[_KEY_DB][_KEY_CREDS] = value

    @property
    def db_connection_string(self):
        """ return the connection string to remote DB
        """
        host = self._config_dict[_KEY_DB][_KEY_DB_HOST]
        port = self._config_dict[_KEY_DB][_KEY_DB_PORT]
        user = quote_plus(self.db_creds[_KEY_DB_CREDS_USR])
        password = quote_plus(self.db_creds[_KEY_DB_CREDS_PWD])
        database = quote_plus(self._config_dict[_KEY_DB][_KEY_DB_NAME])

        return user + ':' + password + '@' + host + ':' + str(port) + '/' + database + '?charset=utf8mb4'

    @property
    def db_echo(self):
        """ return whether to echo the database queries
        """
        return self._config_dict[_KEY_DB].get(_KEY_DB_ECHO, False)

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
