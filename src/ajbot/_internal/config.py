''' contains configuration variables
'''
from pathlib import Path
from urllib.parse import quote_plus
from dataclasses import dataclass

from vbrpytools.dicjsontools import load_json_file, save_json_file

from ajbot._internal.exceptions import OtherException



_MIGRATE_MODE = False        #pylint: disable=global-statement   #on purpose, to be able to change class definition
def set_migrate_mode():
    """ Set migrate mode
    """
    global _MIGRATE_MODE     #pylint: disable=global-statement   #on purpose, to be able to change class definition
    _MIGRATE_MODE = True
def get_migrate_mode():
    """ Get migrate mode
    """
    return _MIGRATE_MODE

AJ_ID_PREFIX = "AJ-"

AJ_SIGNSHEET_FILENAME ="emargement.pdf"

_AJ_CONFIG_PATH = Path(".env")
_AJ_CONFIG_FILE = "ajbot"

_KEY_CREDS = "creds"

_KEY_DISCORD = "discord"
_KEY_GUILD = "guild"
_KEY_ROLES = "roles"
_KEY_OWNERS = "owners"
_KEY_MANAGERS = "managers"
_KEY_MEMBERS = "members"
_KEY_DEFAULT_SUBSCRIBER = "subscriber"
_KEY_DEFAULT_PAST_SUBSCRIBER = "past_subscriber"
_KEY_DEFAULT_MEMBER = "member"

_KEY_ASSO = "asso"
_KEY_ROLE_RESET_TIME_DAYS = "role_reset_time_days"
_KEY_ASSO_FREE_PRESENCE = "free_presence"

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
        discord_roles_cfg = {_KEY_OWNERS: [],
                        _KEY_MANAGERS: [],
                        _KEY_MEMBERS: []}
        asso_roles_cfg = {}
        asso_roles = await aj_db.query_asso_roles(lazyload=False)
        for role in asso_roles:
            if role.is_owner:
                discord_roles_cfg[_KEY_OWNERS] += [dr.id for dr in role.discord_roles if dr.id not in discord_roles_cfg[_KEY_OWNERS]]
            if role.is_manager:
                discord_roles_cfg[_KEY_MANAGERS] += [dr.id for dr in role.discord_roles if dr.id not in discord_roles_cfg[_KEY_MANAGERS]]
            if role.is_member:
                discord_roles_cfg[_KEY_MEMBERS] += [dr.id for dr in role.discord_roles if dr.id not in discord_roles_cfg[_KEY_MEMBERS]]
                if not role.is_owner and not role.is_manager and not role.is_subscriber and not role.is_past_subscriber:
                    # default member role
                    assert _KEY_DEFAULT_MEMBER not in asso_roles_cfg, "Multiple default member asso roles mapped!"
                    asso_roles_cfg[_KEY_DEFAULT_MEMBER] = role.id
            if role.is_subscriber:
                assert _KEY_DEFAULT_SUBSCRIBER not in asso_roles_cfg, "Multiple subscriber asso roles mapped!"
                assert len(role.discord_roles) == 1, "Multiple discord roles mapped to subscriber role!"
                discord_roles_cfg[_KEY_DEFAULT_SUBSCRIBER] = role.discord_roles[0].id
                asso_roles_cfg[_KEY_DEFAULT_SUBSCRIBER] = role.id
            if role.is_past_subscriber:
                assert _KEY_DEFAULT_PAST_SUBSCRIBER not in asso_roles_cfg, "Multiple subscriber asso roles mapped!"
                assert len(role.discord_roles) == 1, "Multiple discord roles mapped to past subscriber role!"
                discord_roles_cfg[_KEY_DEFAULT_PAST_SUBSCRIBER] = role.discord_roles[0].id
                asso_roles_cfg[_KEY_DEFAULT_PAST_SUBSCRIBER] = role.id

        self._config_dict[_KEY_DISCORD][_KEY_ROLES] = discord_roles_cfg
        self._config_dict[_KEY_ASSO][_KEY_ROLES] = asso_roles_cfg

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
        return self._config_dict[_KEY_DISCORD][_KEY_ROLES].get(_KEY_DEFAULT_SUBSCRIBER)

    @property
    def discord_past_subscriber(self):
        """ Returns from config the *single* Discord role IDs having past subscriber attribute.
        """
        return self._config_dict[_KEY_DISCORD][_KEY_ROLES].get(_KEY_DEFAULT_PAST_SUBSCRIBER)

    @property
    def asso_subscriber(self):
        """ Returns from config the asso role IDs having subscriber attribute.
        """
        return self._config_dict[_KEY_ASSO][_KEY_ROLES].get(_KEY_DEFAULT_SUBSCRIBER)

    @property
    def asso_member_default(self):
        """ Returns from config the asso role ID corresponding to member.
        """
        return self._config_dict[_KEY_ASSO][_KEY_ROLES].get(_KEY_DEFAULT_MEMBER)

    @property
    def asso_past_subscriber(self):
        """ Returns from config the asso role IDs having past subscriber attribute.
        """
        return self._config_dict[_KEY_ASSO][_KEY_ROLES].get(_KEY_DEFAULT_PAST_SUBSCRIBER)

    @property
    def asso_role_reset_duration_days(self):
        """ Returns from config the duration in days a user role should be reset.
        """
        return self._config_dict[_KEY_ASSO][_KEY_ROLE_RESET_TIME_DAYS]

    @property
    def asso_free_presence(self):
        """ Returns from config the number of free presence.
        """
        return self._config_dict[_KEY_ASSO][_KEY_ASSO_FREE_PRESENCE]

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
