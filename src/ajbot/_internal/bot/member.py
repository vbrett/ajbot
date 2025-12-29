""" Functions member outputs (Views, buttons, message, ...)
"""
from typing import cast

import discord
from discord import Interaction, ui as dui

from ajbot._internal.config import FormatTypes
from ajbot._internal.ajdb import AjDb, tables as db_t
from ajbot._internal.bot import checks, responses
from ajbot._internal.exceptions import OtherException, AjBotException

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
        await responses.send_response_as_text(interaction=interaction,
                                            content=message,
                                            ephemeral=True)
        return
    [input_member] = input_member

    members = await aj_db.query_members(input_member, 50, False)

    if members:
        if len(members) == 1:
            member = cast(db_t.Member, members[0])

            is_self = False if not member.discord else (member.discord == interaction.user.name)
            editable = is_self or checks.is_manager(interaction)

            view = dui.LayoutView()
            container = dui.Container()
            view.add_item(container)

            if not editable:
                container.add_item(dui.TextDisplay(format(member, FormatTypes.RESTRICTED)))
            else:
                format_style = FormatTypes.FULLCOMPLETE
                container.add_item(dui.TextDisplay(f'# __{member.id}__'))

                text = ''
                if member.credential:
                    text += f"{member.credential:{format_style}}"
                if member.credential and member.discord:
                    text += '\n'
                if member.discord:
                    text += '@' + member.discord
                title = ('Editer' if text else 'Créer') +  ' identité'
                container.add_item(dui.Section(dui.TextDisplay(text),
                                               accessory=EditMemberButton(member=member,
                                                                          title=title,
                                                                          modal_class=EditMemberViewCreds)
                                              ))

                text = "### Adresse(s)\n"
                if member.addresses:
                    text += '\n'.join(f"- {ma.address:{format_style}}" + (" (*)" if ma.principal else "") for ma in member.addresses)
                    title = 'Editer adresse'
                else:
                    text += "Pas d'adresse"
                    title = 'Créer adresse'
                container.add_item(dui.Section(dui.TextDisplay(text),
                                            accessory=EditMemberButton(member=member,
                                                                        title=title,
                                                                        modal_class=EditMemberViewPrincipalAddress)
                                            ))

                text = "### Emails(s)\n"
                if member.emails:
                    text += '\n'.join(f"-  {me.email:{format_style}}" + (" (*)" if me.principal else "") for me in member.emails)
                    title = 'Editer email'
                else:
                    text += "Pas d'email"
                    title = 'Créer email'
                container.add_item(dui.Section(dui.TextDisplay(text),
                                            accessory=EditMemberButton(member=member,
                                                                       title=title,
                                                                       modal_class=EditMemberViewPrincipalEmail)
                                            ))

                text = "### Téléphone(s)\n"
                if member.phones:
                    text += '\n'.join(f"-  {mp.phone:{format_style}}" + (" (*)" if mp.principal else "") for mp in member.phones)
                    title = 'Editer téléphone'
                else:
                    text += "Pas de téléphone"
                    title = 'Créer téléphone'
                container.add_item(dui.Section(dui.TextDisplay(text),
                                            accessory=EditMemberButton(member=member,
                                                                        title=title,
                                                                        modal_class=EditMemberViewPrincipalPhone)
                                            ))

                text = "### Cotisation\n"
                if member.is_subscriber:
                    text += "Cotisant(e) cette saison"
                    title = 'Editer cotisation'
                else:
                    text += "Non cotisant(e) cette saison"
                    title = 'Ajouter cotisation'
                container.add_item(dui.Section(dui.TextDisplay(text),
                                            accessory=EditMemberButton(member=member,
                                                                       title=title,
                                                                       modal_class=EditMemberViewSubscription)
                                            ))

                text = "### Rôle spécifique\n"
                if member.manual_asso_roles:
                    text += '\n'.join(f"-  {mar.name}" for mar in member.manual_asso_roles)  #TODO: add is active role
                    title = 'Editer rôle'
                else:
                    text += "Pas de rôle"
                    title = 'Ajouter rôle'
                container.add_item(dui.Section(dui.TextDisplay(text),
                                            accessory=EditMemberButton(member=member,
                                                                       title=title,
                                                                       modal_class=EditMemberViewSubscription)  #TODO create modal
                                            ))

            await responses.send_response_as_view(interaction=interaction, container=container, ephemeral=True)
        else:
            embed = discord.Embed(color=discord.Color.orange())
            format_style = FormatTypes.FULLSIMPLE if (checks.is_manager(interaction)) else FormatTypes.RESTRICTED
            embed.add_field(name = 'Id', inline=True,
                            value = '\n'.join(str(m.id) for m in members)
                            )
            embed.add_field(name = 'Discord', inline=True,
                            value = '\n'.join(('@' + m.discord) if m.discord else '-' for m in members)
                            )
            embed.add_field(name = 'Nom' + (' (% match)' if len(members) > 1 else ''), inline=True,
                            value = '\n'.join(f'{m.credential:{format_style}}' if m.credential else '-' for m in members)
                            )

            await responses.send_response_as_text(interaction=interaction, content=f"{len(members)} personne(s) trouvé(e)(s)", embed=embed, ephemeral=True)
    else:
        await responses.send_response_as_text(interaction=interaction,
                                            content=f"Je ne connais pas ton ou ta {input_member}.",
                                            ephemeral=True)



# Buttons
# ========================================================
class EditMemberButton(dui.Button):
    """ Class that creates a edit button
    """
    def __init__(self, member, modal_class, title):
        self._member = member
        self._modal_class = modal_class
        super().__init__(style=discord.ButtonStyle.primary,
                         disabled=False,
                         label=title)

    async def callback(self, interaction: discord.Interaction):
        member_modal = await self._modal_class.create(db_member=self._member, interaction=interaction)
        await interaction.response.send_modal(member_modal)


# Modals
# ========================================================
class EditMemberViewCreds(dui.Modal, title='Identité Membre'):
    """ Modal handling member creation / update - Credentials
    """

    def __init__(self):
        self._db_id = None
        self.last_name = None
        self.first_name = None
        self.birthdate = None
        self.discord = None
        super().__init__()

    @classmethod
    async def create(cls, db_member:db_t.Member=None, interaction: discord.Interaction=None):
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

        discord_members = []
        if db_member and db_member.discord:
            discord_members = [m for m in interaction.guild.members if m.name == db_member.discord]
            assert len(discord_members) <= 1, f'More than 1 discord user with same name: {db_member.discord}'


        self.discord = dui.Label(
                            text='Pseudo Discord',
                            component=dui.UserSelect(required=False,
                                                     default_values=discord_members,
                                                    ),
                        )
        self.add_item(self.discord)

        return self

    async def on_error(self, interaction: discord.Interaction, error: Exception):    #pylint: disable=arguments-differ   #No sure why this warning is raised
        """ Event triggered when an error occurs during modal processing
        """
        await responses.send_response_as_text(interaction, f"Une erreur est survenue : {error}\nEt il faut tout refaire...", ephemeral=True)

    # async def on_submit(self, interaction: discord.Interaction):    #pylint: disable=arguments-differ   #No sure why this warning is raised
    #     """ Event triggered when clicking on submit button
    #     """
    #     async with AjDb() as aj_db:

    #         # assert isinstance(self.participants, dui.Label)
    #         # assert isinstance(self.participants.component, dui.TextInput)

    #         # check consistency - event name
    #         event_name = None
    #         if self.event_name.component.value:
    #             event_name = self.event_name.component.value.strip()
    #             if not event_name:
    #                 event_name = None

    #         event = await aj_db.add_update_event(event_id=self._db_id,
    #                                             event_date=event_date,
    #                                             event_name=event_name,
    #                                             participant_ids=participant_ids,)


    #         await display_event(aj_db=aj_db,
    #                             interaction=interaction,
    #                             event_str=str(event))

class EditMemberViewPrincipalAddress(dui.Modal, title='Adresse Principale'):
    """ Modal handling member creation / update - Principal Postal Address
    """

    def __init__(self):
        self._db_id = None
        self.principal = True
        self.street_num = None
        self.street_type = None
        self.street_name = None
        self.zip_code = None
        self.city = None
        # self.extra = None
        super().__init__()

    @classmethod
    async def create(cls, db_member:db_t.Member=None, _interaction: discord.Interaction=None):
        """ awaitable class factory
        """
        self = cls()

        self._db_id = None
        if db_member:
            self._db_id = db_member.id

        address = [ma.address for ma in db_member.addresses if ma.principal]
        match len(address):
            case 0:
                address = None
            case 1:
                address = address[0]
            case _:
                raise AjBotException('More than 1 principal address')

        self.street_num = dui.Label(
                            text='Numéro',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not address)  else str(address.street_num),
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.street_num)

        self.street_type = dui.Label(
                            text='Type voie',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not address)  else str(address.street_type.name),
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.street_type)

        self.street_name = dui.Label(
                            text='Nom voie',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not address)  else str(address.street_name),
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.street_name)

        self.zip_code = dui.Label(
                            text='Code postal',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not address)  else str(address.zip_code),
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.zip_code)

        self.city = dui.Label(
                            text='Ville',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not address)  else str(address.city),
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.city)

        # self.extra = dui.Label(
        #                     text='Autres infos',
        #                     component=dui.TextInput(
        #                                             style=discord.TextStyle.short,
        #                                             required=False,
        #                                             default='' if (not address)  else str(address.extra),
        #                                             max_length=120,
        #                                         ),
        #                 )
        # self.add_item(self.extra)

        return self

    async def on_error(self, interaction: discord.Interaction, error: Exception):    #pylint: disable=arguments-differ   #No sure why this warning is raised
        """ Event triggered when an error occurs during modal processing
        """
        await responses.send_response_as_text(interaction, f"Une erreur est survenue : {error}\nEt il faut tout refaire...", ephemeral=True)

class EditMemberViewPrincipalEmail(dui.Modal, title='Email Principale'):
    """ Modal handling member creation / update - Principal Email
    """

    def __init__(self):
        self._db_id = None
        self.principal = True
        self.email = None
        super().__init__()

    @classmethod
    async def create(cls, db_member:db_t.Member=None, _interaction: discord.Interaction=None):
        """ awaitable class factory
        """
        self = cls()

        self._db_id = None
        if db_member:
            self._db_id = db_member.id

        email = [me.email for me in db_member.emails if me.principal]
        match len(email):
            case 0:
                email = None
            case 1:
                email = email[0]
            case _:
                raise AjBotException('More than 1 principal email')

        self.email = dui.Label(
                            text='addresse',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not email)  else format(email, FormatTypes.FULLCOMPLETE),
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.email)

        return self

    async def on_error(self, interaction: discord.Interaction, error: Exception):    #pylint: disable=arguments-differ   #No sure why this warning is raised
        """ Event triggered when an error occurs during modal processing
        """
        await responses.send_response_as_text(interaction, f"Une erreur est survenue : {error}\nEt il faut tout refaire...", ephemeral=True)

class EditMemberViewPrincipalPhone(dui.Modal, title='Téléphone Principale'):
    """ Modal handling member creation / update - Principal Phone
    """

    def __init__(self):
        self._db_id = None
        self.principal = True
        self.phone = None
        super().__init__()

    @classmethod
    async def create(cls, db_member:db_t.Member=None, _interaction: discord.Interaction=None):
        """ awaitable class factory
        """
        self = cls()

        self._db_id = None
        if db_member:
            self._db_id = db_member.id

        phone = [mp.phone for mp in db_member.phones if mp.principal]
        match len(phone):
            case 0:
                phone = None
            case 1:
                phone = phone[0]
            case _:
                raise AjBotException('More than 1 principal phone')

        self.phone = dui.Label(
                            text='téléphone',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='' if (not phone)  else format(phone, FormatTypes.FULLCOMPLETE),
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.phone)

        return self

    async def on_error(self, interaction: discord.Interaction, error: Exception):    #pylint: disable=arguments-differ   #No sure why this warning is raised
        """ Event triggered when an error occurs during modal processing
        """
        await responses.send_response_as_text(interaction, f"Une erreur est survenue : {error}\nEt il faut tout refaire...", ephemeral=True)

class EditMemberViewSubscription(dui.Modal, title='Cotisation'):
    """ Modal handling member creation / update - subcscription
    """

    def __init__(self):
        self._db_id = None
        self.price = None
        super().__init__()

    @classmethod
    async def create(cls, db_member:db_t.Member=None, _interaction: discord.Interaction=None):
        """ awaitable class factory
        """
        self = cls()

        self._db_id = None
        if db_member:
            self._db_id = db_member.id

        self.price = dui.Label(
                            text='Tarif',
                            component=dui.TextInput(
                                                    style=discord.TextStyle.short,
                                                    required=False,
                                                    default='',
                                                    max_length=120,
                                                ),
                        )
        self.add_item(self.price)


        return self

    async def on_error(self, interaction: discord.Interaction, error: Exception):    #pylint: disable=arguments-differ   #No sure why this warning is raised
        """ Event triggered when an error occurs during modal processing
        """
        await responses.send_response_as_text(interaction, f"Une erreur est survenue : {error}\nEt il faut tout refaire...", ephemeral=True)

if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
