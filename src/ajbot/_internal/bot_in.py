""" List of function to handle app command inputs (decorator, checks, param,...)
"""

from discord import Interaction, app_commands

from ajbot._internal.config import AjConfig
from ajbot._internal.ajdb import AjDb
from ajbot._internal import bot_config
from ajbot._internal.exceptions import OtherException


# Autocomplete & command parameters functions & decorators
# ========================================================
class AutocompleteFactory():
    """ create an autocomplete function based on the result of a db query
    @arg:
        method: name of the AjDb async method to call to get the list of possible values
                Method shall be decorated with @cached_ajdb_method
        attr_name: if set, use this attribute of the returned object as the value (otherwise
                   the string representation of the object is used)

        Note that choice list size is limited, so all matches may not be always returned
    """
    def __init__(self, method, attr_name=None):
        self._method = method
        self._attr = attr_name

    async def ac(self,
                 _interaction: Interaction,
                 current: str,
                ) -> list[app_commands.Choice[str]]:
        """ AutoComplete function
        """
        async with AjDb() as aj_db:
            db_content = await getattr(aj_db, self._method)(keep_detached=True)
            db_content.sort(reverse=True)
            values = [str(row) if not self._attr else str(getattr(row, self._attr)) for row in db_content]

        return [
                app_commands.Choice(name=value, value=value)
                for value in values if current.lower() in value.lower()
               ][:bot_config.AUTOCOMPLETE_LIST_SIZE]


# List of checks that can be used with app commands
# ========================================================
def is_bot_owner(interaction: Interaction) -> bool:
    """A check which only allows the bot owner to use the command."""
    with AjConfig() as aj_config:
        owner_roles = aj_config.discord_owners
    return any(role.id in owner_roles for role in interaction.user.roles)

def is_member(interaction: Interaction) -> bool:
    """A check which only allows members to use the command."""
    with AjConfig() as aj_config:
        member_roles = aj_config.discord_members
    return any(role.id in member_roles for role in interaction.user.roles)

def is_manager(interaction: Interaction) -> bool:
    """A check which only allows managers to use the command."""
    with AjConfig() as aj_config:
        manager_roles = aj_config.discord_managers
    return any(role.id in manager_roles for role in interaction.user.roles)


if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
