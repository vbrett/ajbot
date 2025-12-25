""" List of functions member outputs (Views, buttons, message, ...)
"""

import discord
from discord import Interaction, ui as dui

from ajbot._internal.config import FormatTypes
from ajbot._internal.ajdb import AjDb
from ajbot._internal import bot_in, bot_out, ajdb_tables as ajdb_t
from ajbot._internal.exceptions import OtherException

async def display(aj_db:AjDb,
                  interaction: Interaction,
                  disc_member:discord.Member=None,
                  int_member:int=None,
                  str_member:str=None):
    """ Affiche les infos des membres
    """
    if not interaction.response.type:
        await interaction.response.defer(ephemeral=True,)

    input_member = [x for x in [disc_member, str_member, int_member] if x is not None]
    if len(input_member) != 1:
        input_types="un (et un seul) élément parmi:\r\n* un pseudo\r\n* un nom\r\n* un ID"
        if len(input_member) == 0:
            message = f"😓 Alors là, je vais avoir du mal à trouver sans un minimum d'info, à savoir {input_types}"
        else:
            message = f"🤢 Tu dois fournir {input_types}\r\nMais pas de mélange, c'est pas bon pour ma santé"
        await bot_out.send_response_as_text(interaction=interaction,
                                            content=message,
                                            ephemeral=True)
        return
    [input_member] = input_member

    members = await aj_db.query_members(input_member, 50, False)

    if members:
        if len(members) == 1:
            [member] = members
            is_self = False if not member.discord_pseudo else (member.discord_pseudo.name == interaction.user.name)
            format_style = FormatTypes.FULLSIMPLE if (is_self or bot_in.is_manager(interaction)) else FormatTypes.RESTRICTED
            view = dui.LayoutView()
            container = dui.Container()
            view.add_item(container)

            container.add_item(dui.Section(dui.TextDisplay(format(member, format_style)),
                                           accessory=EditMemberButton(member=member,
                                                                      disabled = (not is_self and not bot_in.is_manager(interaction))
                                                                     )))
            await bot_out.send_response_as_view(interaction=interaction, container=container, ephemeral=True)
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

            await bot_out.send_response_as_text(interaction=interaction, content=f"{len(members)} personne(s) trouvé(e)(s)", embed=embed, ephemeral=True)
    else:
        await bot_out.send_response_as_text(interaction=interaction,
                                            content=f"Je ne connais pas ton ou ta {input_member}.",
                                            ephemeral=True)



# Buttons
# ========================================================
class EditMemberButton(dui.Button):
    """ Class that creates a edit button
    """
    def __init__(self, member, disabled):
        self._member = member
        super().__init__(style=discord.ButtonStyle.primary,
                         label='Editer',
                         disabled = disabled)

    async def callback(self, interaction: discord.Interaction):
        async with AjDb() as aj_db:
            member_modal = await EditMemberView.create(aj_db=aj_db, db_member=self._member)
            await interaction.response.send_modal(member_modal)


# Modals
# ========================================================
class EditMemberView(dui.Modal, title='Membre'):
    """ Modal handling member creation / update
    """

    def __init__(self):
        self._db_id = None
        self.last_name = None
        self.first_name = None
        self.discord_pseudo = None
        self.birthdate = None
        super().__init__()

    @classmethod
    async def create(cls, aj_db:AjDb, db_member:ajdb_t.Member=None):
        """ awaitable class factory
        """
        self = cls()

        self._db_id = None
        if db_member:
            self._db_id = db_member.id

        self.last_name = dui.Label(
                            text='Nom de famille',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not db_member or not db_member.credential)  else db_member.credential.last_name,
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.last_name)

        self.first_name = dui.Label(
                            text='Prénom',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not db_member or not db_member.credential) else db_member.credential.first_name,
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.first_name)

        self.discord_pseudo = dui.Label(
                            text='Pseudo Discord',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not db_member or not db_member.discord_pseudo) else db_member.discord_pseudo.name,
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.discord_pseudo)

        self.birthdate = dui.Label(
                            text='Date de naissance',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not db_member or not db_member.credential) else str(db_member.credential.birthdate),
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.birthdate)

        return self

    # async def on_submit(self, interaction: discord.Interaction):    #pylint: disable=arguments-differ   #No sure why this warning is raised
    #     """ Event triggered when clicking on submit button
    #     """
    #     async with AjDb() as aj_db:

    #         assert isinstance(self.participants, dui.Label)
    #         assert isinstance(self.participants.component, dui.TextInput)

    #         # check consistency - date
    #         event_date = None
    #         if not self._db_id:
    #             assert isinstance(self.event_date, dui.Label)
    #             assert isinstance(self.event_date.component, dui.TextInput)

    #             try:
    #                 event_date = date_parser.parse(self.event_date.component.value, dayfirst=True).date()
    #             except date_parser.ParserError:
    #                 await send_response_as_text(interaction, f"La date '{self.event_date.component.value}' n'est pas valide.", ephemeral=True)
    #                 return

    #         # check consistency - event name
    #         event_name = None
    #         if self.event_name.component.value:
    #             event_name = self.event_name.component.value.strip()
    #             if not event_name:
    #                 event_name = None

    #         # check consistency - participants
    #         try:
    #             participant_ids = list(set(int(i.strip()) for i in self.participants.component.value.split(',') if i.strip()))
    #         except ValueError:
    #             await send_response_as_text(interaction, "La liste des participants n'est pas valide.\r\nIl faut une liste de nombres.", ephemeral=True)
    #             return

    #         event = await aj_db.add_update_event(event_id=self._db_id,
    #                                             event_date=event_date,
    #                                             event_name=event_name,
    #                                             participant_ids=participant_ids,)


    #         await display_event(aj_db=aj_db,
    #                             interaction=interaction,
    #                             event_str=str(event))

    async def on_error(self, interaction: discord.Interaction, error: Exception):    #pylint: disable=arguments-differ   #No sure why this warning is raised
        """ Event triggered when an error occurs during modal processing
        """
        await bot_out.send_response_as_text(interaction, f"Une erreur est survenue lors de la création / modification du membre : {error}\nEt il faut tout refaire...", ephemeral=True)


if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
