''' contains configuration variables
'''
from pathlib import Path
from urllib.parse import quote_plus
from dataclasses import dataclass

from vbrpytools.dicjsontools import load_json_file, save_json_file

from ajbot._internal.exceptions import OtherException

AJ_ID_PREFIX = "AJ-"

_AJ_CONFIG_PATH = Path(".env")
_AJ_CONFIG_FILE = "ajbot"

_KEY_CREDS = "creds"

_KEY_DISCORD = "discord"
_KEY_GUILD = "guild"
_KEY_ROLES = "roles"
_KEY_OWNERS = "owners"
_KEY_MANAGERS = "managers"
_KEY_MEMBERS = "members"
_KEY_SUBSCRIBER = "subscriber"
_KEY_PAST_SUBSCRIBER = "past_subscriber"

_KEY_ASSO = "asso"


_KEY_DB = "db"
_KEY_DB_HOST = "host"
_KEY_DB_PORT = "port"
_KEY_DB_CREDS_USR = "user"
_KEY_DB_CREDS_PWD = "password"
_KEY_DB_NAME = "db_name"
_KEY_DB_ECHO = "db_echo"
_KEY_CACHE_TIME_SEC = "db_cache_time_sec"

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

    async def udpate_roles(self, aj_db):
        """ Load from DB the roles mapping and update config accordingly.
        """
        discord_roles = {_KEY_OWNERS: [],
                        _KEY_MANAGERS: [],
                        _KEY_MEMBERS: []}
        asso_roles = {}
        mapped_roles = await aj_db.query_discord_asso_roles()
        for mr in mapped_roles:
            # mr = cast(ajdb_t.AssoRoleDiscordRole, mr)
            if mr.asso_role.is_owner and mr.discord_role_id not in discord_roles[_KEY_OWNERS]:
                discord_roles[_KEY_OWNERS].append(mr.discord_role_id)
            if mr.asso_role.is_manager and mr.discord_role_id not in discord_roles[_KEY_MANAGERS]:
                discord_roles[_KEY_MANAGERS].append(mr.discord_role_id)
            if mr.asso_role.is_member and mr.discord_role_id not in discord_roles[_KEY_MEMBERS]:
                discord_roles[_KEY_MEMBERS].append(mr.discord_role_id)
            if mr.asso_role.is_subscriber:
                assert discord_roles.get(_KEY_SUBSCRIBER, mr.discord_role_id) == mr.discord_role_id, "Multiple subscriber discord roles mapped!"
                assert asso_roles.get(_KEY_SUBSCRIBER, mr.asso_role_id) == mr.asso_role_id, "Multiple subscriber asso roles mapped!"
                discord_roles[_KEY_SUBSCRIBER] = mr.discord_role_id
                asso_roles[_KEY_SUBSCRIBER] = mr.asso_role_id
            if mr.asso_role.is_past_subscriber:
                assert discord_roles.get(_KEY_PAST_SUBSCRIBER, mr.discord_role_id) == mr.discord_role_id, "Multiple past subscriber discord roles mapped!"
                assert asso_roles.get(_KEY_PAST_SUBSCRIBER, mr.asso_role_id) == mr.asso_role_id, "Multiple past subscriber asso roles mapped!"
                discord_roles[_KEY_PAST_SUBSCRIBER] = mr.discord_role_id
                asso_roles[_KEY_PAST_SUBSCRIBER] = mr.asso_role_id

        self._config_dict[_KEY_DISCORD][_KEY_ROLES] = discord_roles
        self._config_dict[_KEY_ASSO][_KEY_ROLES] = asso_roles

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
    def discord_owners(self):
        """ Returns from config the Discord roles IDs having owner attribute.
        """
        return self._config_dict[_KEY_DISCORD][_KEY_ROLES].get(_KEY_OWNERS)

    @property
    def discord_managers(self):
        """ Returns from config the Discord roles IDs having manager attribute.
        """
        return self._config_dict[_KEY_DISCORD][_KEY_ROLES].get(_KEY_MANAGERS)

    @property
    def discord_members(self):
        """ Returns from config the Discord roles IDs having member attribute.
        """
        return self._config_dict[_KEY_DISCORD][_KEY_ROLES].get(_KEY_MEMBERS)

    @property
    def discord_subscriber(self):
        """ Returns from config the *single* Discord role IDs having subscriber attribute.
        """
        return self._config_dict[_KEY_DISCORD][_KEY_ROLES].get(_KEY_SUBSCRIBER)

    @property
    def discord_past_subscriber(self):
        """ Returns from config the *single* Discord role IDs having past subscriber attribute.
        """
        return self._config_dict[_KEY_DISCORD][_KEY_ROLES].get(_KEY_PAST_SUBSCRIBER)

    @property
    def asso_subscriber(self):
        """ Returns from config the asso role IDs having subscriber attribute.
        """
        return self._config_dict[_KEY_ASSO][_KEY_ROLES].get(_KEY_SUBSCRIBER)

    @property
    def asso_past_subscriber(self):
        """ Returns from config the asso role IDs having past subscriber attribute.
        """
        return self._config_dict[_KEY_ASSO][_KEY_ROLES].get(_KEY_PAST_SUBSCRIBER)

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
    def db_cache_time_sec(self):
        """ return the cache time in seconds
        """
        return self._config_dict[_KEY_DB][_KEY_CACHE_TIME_SEC]

    @property
    def db_echo(self):
        """ return whether to echo the database queries
        """
        return self._config_dict[_KEY_DB].get(_KEY_DB_ECHO, False)

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
