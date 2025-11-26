""" List of function to handle app command outputs (Views, buttons, message, ...)
"""
from datetime import datetime, date
import dateutil.parser as date_parser

import discord
from discord import Interaction, ui as dui

from ajbot._internal.config import FormatTypes
from ajbot._internal.ajdb import AjDb
from ajbot._internal import bot_in, bot_config
from ajbot._internal.exceptions import OtherException


# Generic Display functions
# ========================================================
async def send_response_as_text(interaction: Interaction,
                                content:str, ephemeral=False, delete_after=None,
                                chunk_size=bot_config.CONTENT_MAX_SIZE, split_on_eol=True):
    """ Send basic command response, handling splitting it if needed based on discord limit.
        Can also ensure that split is only perform at eol.
    """
    assert (chunk_size <= bot_config.CONTENT_MAX_SIZE), f"La taille demandée {chunk_size} n'est pas supportée. Max {bot_config.CONTENT_MAX_SIZE}."

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


# Member, event,.. detail display
# ========================================================
async def display_member(interaction: Interaction,
                         disc_member:discord.Member=None,
                         int_member:int=None,
                         str_member:str=None):
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

        if members:
            if len(members) == 1:
                class EditButton(dui.Button):
                    """ Class that creates a edit button
                    """
                    def __init__(self):
                        super().__init__(style=discord.ButtonStyle.primary,
                                         label='Editer',
                                         disabled = not bot_in.is_manager(interaction))

                    async def callback(self, interaction: discord.Interaction):
                        await send_response_as_text(interaction, content="Pas encore disponible", ephemeral=True, delete_after=10)

                [member] = members
                is_self = member.discord_pseudo.name == interaction.user.name
                format_style = FormatTypes.FULLSIMPLE if (is_self or bot_in.is_manager(interaction)) else FormatTypes.RESTRICTED
                view = dui.LayoutView()
                container = dui.Container()
                view.add_item(container)

                container.add_item(dui.Section(dui.TextDisplay(format(member, format_style)),
                                                accessory=EditButton()))
                await interaction.response.send_message(view=view, ephemeral=True)
            else:
                embed = discord.Embed(color=discord.Color.orange())
                format_style = FormatTypes.FULLSIMPLE if (bot_in.is_manager(interaction)) else FormatTypes.RESTRICTED
                embed.add_field(name = 'Id', inline=True,
                                value = '\n'.join(str(m.id) for m in members)
                                )
                embed.add_field(name = 'Discord', inline=True,
                                value = '\n'.join(('@' + str(m.discord_pseudo.name)) if m.discord_pseudo else '-' for m in members)
                                )
                embed.add_field(name = 'Nom' + (' (% match)' if len(members) > 1 else ''), inline=True,
                                value = '\n'.join(f'{m.credential:{format_style}}' if m.credential else '-' for m in members)
                                )

                await interaction.response.send_message(content=f"{len(members)} personne(s) trouvé(e)(s)", embed=embed, ephemeral=True)
        else:
            await send_response_as_text(interaction=interaction,
                                        content=f"Je ne connais pas ton ou ta {input_member}.",
                                        ephemeral=True)


async def display_event(interaction: Interaction,
                        season_name:str=None,
                        event_str:str=None):
    """ Affiche les infos des évènements
    """
    input_event = [x for x in [season_name, event_str] if x is not None]

    if len(input_event) == 0:
        eventmodal = await CreateEventView.create()
        await interaction.response.send_modal(eventmodal)
        return

    if len(input_event) > 1:
        input_types="un (et un seul) élément parmi:\r\n* une saison\r\n* un évènement"
        message = f"🤢 Tu dois fournir {input_types}\r\nMais pas de mélange, c'est pas bon pour ma santé"
        await send_response_as_text(interaction=interaction,
                                    content=message,
                                    ephemeral=True)
        return

    async with AjDb() as aj_db:
        events = await aj_db.query_events(season_name=season_name, event_str=event_str)

        if events:
            format_style = FormatTypes.FULLSIMPLE if bot_in.is_manager(interaction) else FormatTypes.RESTRICTED
            if len(events) == 1:
                [event] = events
                class _EditButton(dui.Button):
                    """ Class that creates a edit button
                    """
                    def __init__(self):
                        super().__init__(style=discord.ButtonStyle.primary,
                                         label='Editer',
                                         disabled = not bot_in.is_manager(interaction))

                    async def callback(self, interaction: discord.Interaction):
                        eventmodal = await CreateEventView.create(event)
                        await interaction.response.send_modal(eventmodal)

                class _DeleteButton(dui.Button):
                    """ Class that creates a edit button
                    """
                    def __init__(self):
                        super().__init__(style=discord.ButtonStyle.red,
                                         label='Supprimer',
                                         disabled = not bot_in.is_manager(interaction))

                    async def callback(self, interaction: discord.Interaction):
                        await send_response_as_text(interaction=interaction, content="Pas encore disponible", ephemeral=True)

                view = dui.LayoutView()
                container = dui.Container()
                view.add_item(container)

                participants = [m.member for m in event.members]
                participants.sort(key=lambda x:x.credential)
                message1 = f"# {event:{format_style}}"
                message2 = f"## {len(participants)} participant" + ('' if not participants else (('s' if len(participants) > 1 else '') + " :"))
                container.add_item(dui.Section(dui.TextDisplay(message1), accessory=_EditButton()))
                container.add_item(dui.Section(dui.TextDisplay(message2), accessory=_DeleteButton()))
                if participants:
                    container.add_item(dui.TextDisplay('>>> ' + '\n'.join(f'{m:{format_style}}' for m in participants)))
                await interaction.response.send_message(view=view, ephemeral=True)
            else:
                embed = discord.Embed(color=discord.Color.blue())
                embed.add_field(name = 'date', inline=True,
                                value = '\n'.join(str(e.date) for e in events)
                                )
                embed.add_field(name = 'Nom', inline=True,
                                value = '\n'.join(e.name if e.name else '-' for e in events)
                                )
                embed.add_field(name = 'Présence', inline=True,
                                value = '\n'.join(str(len(e.members)) for e in events)
                                )

                await interaction.response.send_message(content=f"{len(events)} évènement(s) trouvé(s) :", embed=embed, ephemeral=True)
        else:
            await send_response_as_text(interaction=interaction,
                                        content="Je n'ai trouvé aucun évènement.",
                                        ephemeral=True)



# Member, event.. edit modals
# ========================================================
class CreateEventView(dui.Modal, title='Evènement'):
    """ Modal handling event creation / update
    """
    @classmethod
    async def create(cls, db_event=None):
        """ awaitable class factory
        """
        self = cls()

        self._db_event_id = None
        present_members = None
        if db_event:
            self._db_event_id = db_event.id

            async with AjDb() as aj_db:
                present_members = await aj_db.query_members_per_event_presence(db_event.id)
                if present_members:
                    present_members.sort()


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
                                                    default='' if not present_members else ', '.join(str(int(p.id)) for p in present_members),
                                                    max_length=bot_config.COMPONENT_TEXT_SIZE,
                                                ),
                        )
        self.add_item(self.participants)
        return self

    async def on_submit(self, interaction: discord.Interaction):    #pylint: disable=arguments-differ   #No sure why this warning is raised
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
                await send_response_as_text(interaction, f"La date '{self.event_date.component.value}' n'est pas valide.", ephemeral=True)
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
            await send_response_as_text(interaction, "La liste des participants n'est pas valide.\r\nIl faut une liste de nombres.", ephemeral=True)
            return

        async with AjDb() as aj_db:
            event = await aj_db.add_update_event(event_id=self._db_event_id,
                                                 event_date=event_date,
                                                 event_name=event_name,
                                                 participant_ids=participant_ids,)


        await display_event(interaction=interaction, event_str=str(event))

    def __init__(self):
        self._db_event_id = None
        self.event_date = None
        self.event_name = None
        self.participants = None
        super().__init__()


if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
