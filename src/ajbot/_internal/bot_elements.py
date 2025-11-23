""" Functions, Views & buttons used by bot
"""
from functools import wraps
from typing import Optional
from datetime import datetime, timedelta

import discord
from discord import app_commands, Interaction, ui as dui

from ajbot._internal.ajdb import AjDb
from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal.exceptions import OtherException
from ajbot._internal.config import AjConfig



class AutocompleteFactory():
    """ create an autocomplete function based on the content of a db table
    """
    def __init__(self, table_class, attr_name, refresh_rate_in_sec=60):
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
            self._values = [str(getattr(row, self._attr)) for row in db_content]
            self._last_refresh = datetime.now()

        return [
            app_commands.Choice(name=value, value=value)
            for value in self._values if current.lower() in value.lower()
        ]


def with_season_name(func):
    """ Decorator to handle command season parameter with autocomplete
    """
    @wraps(func)
    @app_commands.rename(season_name='saison')
    @app_commands.describe(season_name='la saison à analyser (aucune = saison en cours)')
    @app_commands.autocomplete(season_name=AutocompleteFactory(ajdb_t.Season, 'name').ac)
    async def wrapper(*args, season_name:Optional[str]=None, **kwargs):
        result = await func(*args, season_name, **kwargs)
        return result

    return wrapper


def get_discord_members(discord_client, guild_names=None):
    """ Returns a dictionary of members info from a list of discord guilds.
        guilds: list of guild names to include members from.
                If None, all guilds the bot is in are used.
    """
    return {"date": discord.utils.utcnow().isoformat(),
            "members": {guild.name: {member.id: {
                                                'name': member.name,
                                                'disp_name': member.display_name,
                                                'joined_at': member.joined_at.isoformat(),
                                                'roles': [role.name for role in member.roles]
                                                }
                                    for member in guild.members}
                        for guild in discord_client.guilds
                        if guild_names is None or guild.name in guild_names}
            }


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
