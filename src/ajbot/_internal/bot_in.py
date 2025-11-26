""" List of function to handle app command inputs (decorator, checks, param,...)
"""
from functools import wraps
from typing import Optional
from datetime import datetime, timedelta

from discord import Interaction, app_commands

from ajbot._internal.config import AjConfig
from ajbot._internal.ajdb import AjDb
from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal import bot_config
from ajbot._internal.exceptions import OtherException


# Autocomplete & command parameters functions & decorators
# ========================================================
class AutocompleteFactory():
    """ create an autocomplete function based on the content of a db table
        Note that choice list size is limited, so all matches may not be always returned
    """
    def __init__(self, table_class, attr_name=None, refresh_rate_in_sec=60):
        self._table = table_class
        self._attr = attr_name
        self._values = None
        self._last_refresh = None
        self._refresh_in_sec = refresh_rate_in_sec

    async def ac(self,
                 _interaction: Interaction,
                 current: str,
                ) -> list[app_commands.Choice[str]]:
        """ AutoComplete function
        """
        if not self._values or self._last_refresh < (datetime.now() - timedelta(seconds=self._refresh_in_sec)):
            async with AjDb() as aj_db:
                db_content = await aj_db.query_table_content(self._table)
            db_content.sort(reverse=True)
            self._values = [str(row) if not self._attr else str(getattr(row, self._attr)) for row in db_content]
            self._last_refresh = datetime.now()

        return [
                app_commands.Choice(name=value, value=value)
                for value in self._values if current.lower() in value.lower()
               ][:bot_config.AUTOCOMPLETE_LIST_SIZE]


# List of checks that can be used with app commands
# ========================================================
def is_bot_owner(interaction: Interaction) -> bool:
    """A check which only allows the bot owner to use the command."""
    with AjConfig() as aj_config:
        bot_owner = aj_config.discord_bot_owner
    return interaction.user.id == bot_owner

def is_member(interaction: Interaction) -> bool:
    """A check which only allows members to use the command."""
    with AjConfig() as aj_config:
        member_roles = aj_config.discord_role_member
    return any(role.id in member_roles for role in interaction.user.roles)

def is_manager(interaction: Interaction) -> bool:
    """A check which only allows managers to use the command."""
    with AjConfig() as aj_config:
        manager_roles = aj_config.discord_role_manager
    return any(role.id in manager_roles for role in interaction.user.roles)


if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
