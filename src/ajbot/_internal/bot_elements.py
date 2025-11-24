""" Functions, Views & buttons used by bot
"""
from functools import wraps
from typing import Optional
from datetime import datetime, timedelta, date
import dateutil.parser as date_parser

import discord
from discord import app_commands, Interaction, ui as dui

from ajbot._internal.ajdb import AjDb
from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal.exceptions import OtherException
from ajbot._internal.config import AjConfig


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


# Autocomplete & command parameters functions & decorators
# ========================================================
class AutocompleteFactory():
    """ create an autocomplete function based on the content of a db table
        Choice list is limited to 25, so keep the last 25 if needed
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
            self._values = [str(row) if not self._attr else str(getattr(row, self._attr)) for row in db_content]
            self._last_refresh = datetime.now()

        return [
            app_commands.Choice(name=value, value=value)
            for value in self._values if current.lower() in value.lower()
        ][-25:]


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


# Create event modal view
# ========================================================
class CreateEventModal(dui.Modal, title='Evènement'):
    """ Modal handling event creation / update
    """
    @classmethod
    async def create(cls, input_event_name:str=None):
        """ awaitable class factory
        """
        self = cls()

        self._db_event_id = None
        db_event = None
        async with AjDb() as aj_db:
            if input_event_name:
                events = await aj_db.query_table_content(ajdb_t.Event)
                [db_event] = [e for e in events if str(e) == input_event_name]
                self._db_event_id = db_event.id

                self.present_members = await aj_db.query_members_per_event_presence(db_event.id)
                if self.present_members:
                    self.present_members.sort()


        if db_event:
            self.event_date = dui.TextDisplay(str(date(db_event.date.year,
                                                       db_event.date.month,
                                                       db_event.date.day)))
        else:
            self.event_date = dui.Label(
                                text='Date',
                                description="Date de l'évènement",
                                component=dui.TextInput(
                                                        style=discord.TextStyle.short,
                                                        required=True,
                                                        placeholder=str(datetime.now().date()),
                                                        max_length=120,
                                                    ),
                            )
        self.add_item(self.event_date)

        self.event_name = dui.Label(
                            text='Nom',
                            description="Nom de l'évènement (laisser vide pour une soirée classique)",
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if not db_event else db_event.name,
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.event_name)

        self.participants = dui.Label(
                            text='Participants',
                            description="Liste des identifiants des membres ayant participé à l'évènement, séparés par des virgules",
                            component=dui.TextInput(
                                                    style=discord.TextStyle.paragraph,
                                                    required=False,
                                                    default='' if not self.present_members else ', '.join(str(int(p.id)) for p in self.present_members),
                                                    max_length=4000,
                                                ),
                        )
        self.add_item(self.participants)

        # TODO: when (if...) select component supports more than 25 items, or if modal supports more than 5 components, implement it
        # members.sort()
        # participants_options = [discord.SelectOption(label=format(m,FormatTypes.FULLSIMPLE),
        #                                              description='',
        #                                              default=m in participants) for m in members]
        #
        # self.participants = []
        # for particip_chunk in divide_list(participants_options, 25):
        #     self.participants.append(dui.Label(
        #                             text='Participants',
        #                             description="Liste des participants à l'évènement",
        #                             component=dui.Select(
        #                                                 placeholder='choisissez les participants',
        #                                                 options=particip_chunk,
        #                                                 max_values=len(particip_chunk)
        #                                                 ),
        #                             ))
        #     self.add_item(self.participants[-1])

        return self

    async def on_submit(self, interaction: discord.Interaction):
        """ Event triggered when clicking on submit button
        """

        assert isinstance(self.participants, dui.Label)
        assert isinstance(self.participants.component, dui.TextInput)

        # check consistency - date
        event_date = None
        if not self._db_event_id:
            assert isinstance(self.event_date, dui.Label)
            assert isinstance(self.event_date.component, dui.TextInput)

            try:
                event_date = date_parser.parse(self.event_date.component.value, dayfirst=True).date()
            except date_parser.ParserError:
                await interaction.response.send_message(f"La date '{self.event_date.component.value}' n'est pas valide.", ephemeral=True)
                return

        # check consistency - event name
        event_name = None
        if self.event_name.component.value:
            event_name = self.event_name.component.value.strip()
            if not event_name:
                event_name = None

        # check consistency - participants
        try:
            participant_ids = [int(i.strip()) for i in self.participants.component.value.split(',') if i.strip()]
        except ValueError:
            await interaction.response.send_message("La liste des participants n'est pas valide.\r\nIl faut une liste de nombres.", ephemeral=True)
            return

        async with AjDb() as aj_db:
            await aj_db.add_update_event(event_id=self._db_event_id,
                                         event_date=event_date,
                                         event_name=event_name,
                                         participant_ids=participant_ids,)

        await interaction.response.send_message("C'est fait!", ephemeral=True)

    def __init__(self):
        self._db_event_id = None
        self.event_date = None
        self.event_name = None
        self.present_members = None
        self.participants = None
        super().__init__()


if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
