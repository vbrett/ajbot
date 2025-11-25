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
from ajbot._internal.exceptions import AjBotException, OtherException
from ajbot._internal.config import AjConfig, FormatTypes


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


def with_event_name(func):
    """ Decorator to handle command season parameter with autocomplete
    """
    @wraps(func)
    @app_commands.rename(event='évènement')
    @app_commands.describe(event='évènement à modifier (aucun = crée un nouvel évènement)')
    @app_commands.autocomplete(event=AutocompleteFactory(ajdb_t.Event).ac)
    async def wrapper(*args, event:Optional[str]=None, **kwargs):
        result = await func(*args, event, **kwargs)
        return result

    return wrapper

# Display functions
# ========================================================
async def send_response_as_text(interaction: Interaction,
                                content:str, ephemeral=False, delete_after=None,
                                chunk_size=1800, split_on_eol=True):
    """ Send basic command response, handling splitting it if needed (limit = 2000 characters).
        Can also ensure that split is only perform at eol.
    """
    if chunk_size > 1980:
        raise AjBotException(f"La taille demandée {chunk_size} n'est pas supportée. Max 2000.")

    first_answer = True
    i = 0
    while i < len(content):
        chunk = content[i:i + chunk_size]
        if split_on_eol and (i + chunk_size) < len(content):
            split_last_line = chunk.rsplit('\n', 1)
            if len(split_last_line) > 1:
                chunk = split_last_line[0]
                i -= len(split_last_line[1])
        i += chunk_size
        if first_answer:
            await interaction.response.send_message(chunk, ephemeral=ephemeral, delete_after=delete_after)
            first_answer = False
        else:
            await interaction.followup.send('(...)\n' + chunk, ephemeral=ephemeral, delete_after=delete_after)

async def send_response_as_view(interaction: Interaction,
                                title:str, summary:str, content:str,
                                ephemeral=False,):
    """ Send command response as a view
    """
    view = dui.LayoutView()
    container = dui.Container()
    view.add_item(container)

    container.add_item(dui.TextDisplay(f'# __{title}__'))
    container.add_item(dui.TextDisplay(f'## {summary}'))
    container.add_item(dui.TextDisplay(f'>>> {content}'))

    timestamp = discord.utils.format_dt(interaction.created_at, 'F')
    footer = dui.TextDisplay(f'-# Généré par {interaction.user} (ID: {interaction.user.id}) | {timestamp}')

    container.add_item(footer)
    await interaction.response.send_message(view=view, ephemeral=ephemeral)


async def send_member_info(interaction: Interaction,
                           disc_member:discord.Member=None,
                           int_member:int=None,
                           str_member:str=None,
                           delete_after=None):
    """ Affiche les infos des membres
    """
    input_member = [x for x in [disc_member, str_member, int_member] if x is not None]
    if len(input_member) != 1:
        input_types="un (et un seul) élément parmi:\r\n* un pseudo\r\n* un nom\r\n* un ID"
        if len(input_member) == 0:
            message = f"😓 Alors là, je vais avoir du mal à trouver sans un minimum d'info, à savoir {input_types}"
        else:
            message = f"🤢 Tu dois fournir {input_types}\r\nMais pas de mélange, c'est pas bon pour ma santé"
        await send_response_as_text(interaction=interaction,
                                    content=message,
                                    ephemeral=True)
        return
    [input_member] = input_member

    async with AjDb() as aj_db:
        members = await aj_db.query_members_per_id_info(input_member, 50, False)

    embed = None
    view = None
    reply = None
    if members:
        if len(members) == 1:
            class EditButton(dui.Button):
                """ Class that creates a edit button
                """
                def __init__(self):
                    super().__init__(style=discord.ButtonStyle.primary, label='Editer', row=2)

                async def callback(self, interaction: discord.Interaction):
                    await interaction.response.send_message(content="Pas encore disponible", ephemeral=True, delete_after=10)

            [member] = members
            is_self = member.discord_pseudo.name == interaction.user.name
            format_style = FormatTypes.FULLSIMPLE if (is_self or is_manager(interaction)) else FormatTypes.RESTRICTED
            view = dui.LayoutView()
            container = dui.Container()
            view.add_item(container)

            container.add_item(dui.Section(dui.TextDisplay(format(member, format_style)),
                                            accessory=EditButton()))
        else:
            #TODO: transform embed to view - once view can support tables
            embed = discord.Embed(color=discord.Color.orange())
            format_style = FormatTypes.FULLSIMPLE if (is_manager(interaction)) else FormatTypes.RESTRICTED
            embed.add_field(name = 'id', inline=True,
                            value = '\n'.join(str(m.id) for m in members)
                            )
            embed.add_field(name = 'Discord', inline=True,
                            value = '\n'.join(('@' + str(m.discord_pseudo.name)) if m.discord_pseudo else '' for m in members)
                            )
            embed.add_field(name = 'Nom' + (' (% match)' if len(members) > 1 else ''), inline=True,
                            value = '\n'.join(f'{m.credential:{format_style}}' if m.credential else '' for m in members)
                            )

            reply = "Voilà ce que j'ai trouvé:"
    else:
        reply = f"Je ne connais pas ton ou ta {input_member}."

    await interaction.response.send_message(content=reply, embed=embed, view=view, ephemeral=True, delete_after=delete_after)


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
class CreateEventView(dui.Modal, title='Evènement'):
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
