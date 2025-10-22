""" test ing discord.py library
"""
import sys
from typing import Optional
from pathlib import Path

import discord
from discord import app_commands

from ajbot import credentials
from ajbot._internal.ajdb import AjDb, AjDate, AjEvent
from ajbot._internal.exceptions import CredsException
from ajbot._internal.config import DATEPARSER_CONFIG, AjConfig


class MyClient(discord.Client):
    """
    A basic client subclass which includes a CommandTree for application commands.
    Parameters
    ----------
    intents: discord.Intents
        The intents to use for this client.
    guild: discord.Object
        The guild in which this slash command will be registered.
    """

    # Suppress error on the User attribute being None since it fills up later
    user: discord.ClientUser

    def __init__(self, *, intents: discord.Intents, guild: discord.Object):
        super().__init__(intents=intents)
        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.
        self.tree = app_commands.CommandTree(self)
        self._guild = guild

    # We synchronize the app commands to one single guild.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self):
        """This copies the global commands over to your guild."""
        self.tree.copy_global_to(guild=self._guild)
        await self.tree.sync(guild=self._guild)
        print("commands synced to guild")


class MyAppEventsAndCommands():
    """ class to encapsulate events and commands of the bot
    """
    client : MyClient

    def __init__(self,
                 aj_config:AjConfig,
                 intents:discord.Intents):

        self.aj_config = aj_config

        self.aj_db = AjDb(aj_config)

        self.last_hello_member : discord.User = None

        self.client = MyClient(intents=intents,
                               guild=discord.Object(aj_config.discord_guild))

        # List of events for the bot
        # ========================================================
        @self.client.event
        async def on_ready():
            print(f'Logged in as {self.client.user} (ID: {self.client.user.id})')
            print('------')

        # List of commands for the bot
        # ========================================================
        @self.client.tree.command()
        async def hello(interaction: discord.Interaction):
            """Dis bonjour à l'utilisateur."""
            if interaction.user == self.last_hello_member:
                message = "Toi encore ?\r\nT'as rien de mieux à faire ?"
            else:
                self.last_hello_member = interaction.user
                message = f'Bonjour {interaction.user.mention}!'
            await interaction.response.send_message(message)

        @self.client.tree.command(name="membre")
        # @app_commands.checks.has_role("bureau")
        # @app_commands.checks.has_permissions(manage_roles=True)
        @app_commands.rename(in_member='pseudo')
        @app_commands.rename(str_member='nom')
        @app_commands.describe(in_member='pseudo discord.')
        @app_commands.describe(str_member='nom (ID, nom complet ou partiel)')
        async def member(interaction: discord.Interaction, in_member:Optional[discord.Member]=None, str_member:Optional[str]=None):
            """ Affiche les infos des membres. Parametre = ID, pseudo discord ou nom (complet ou partiel)
                paramètre au choix:
                    - ID (ex: 12, 124)
                    - pseudo_discord (ex: VbrBot)
                    - prénom nom ou nom prénom (sans guillement)
                    supporte des valeurs approximatives comme
                        - nom ou prenom seul
                        - nom et/ou prénom approximatif
                    retourne alors une liste avec la valeur de match
            """
            await self.send_member_info(interaction, in_member, str_member)

        # @MyClient.tree.command(name="recharger_db")
        # @app_commands.check(self._is_manager)
        # async def reload_db(interaction: discord.Interaction):
        #     """ Recharge le fichier excel de la base de données depuis Google Drive.
        #     """
        #     self.aj_db.load_db()
        #     await interaction.response.send_message("C'est fait !", ephemeral=True)


        # # List of context menu commands for the bot
        # # ========================================================

        @self.client.tree.context_menu(name='Nom du membre')
        async def show_name(interaction: discord.Interaction, member: discord.Member):
            await self.send_member_info(interaction, member, None, 5)


    async def send_member_info(self, interaction: discord.Interaction,
                               in_member:discord.Member=None, str_member:str=None,
                               delete_after=None):
        """ Affiche les infos des membres
        """
        if in_member and str_member:
            await interaction.response.send_message("Tu peux fournir soit un pseudo, soit un nom, mais pas les deux.",
                                                    ephemeral=True, delete_after=5)
            return

        members = await self.aj_db.members.search(in_member, str_member, 50, False)

        if members:
            if interaction.user.guild_permissions.manage_roles:
                reply = "\r\n".join([f"{member:manager}" for member in members])
            else:
                reply = "\r\n".join([f"{member:user}" for member in members])
        else:
            reply = f"Je connais pas ton {in_member}."

        await interaction.response.send_message(reply, ephemeral=True, delete_after=delete_after)


    # List of checks that can be used with app commands
    # ========================================================
    def _is_bot_owner(self, interaction: discord.Interaction) -> bool:
        """A check which only allows the bot owner to use the command."""
        return interaction.user.id == self.aj_config.discord_bot_owner

    def _is_manager(self, interaction: discord.Interaction) -> bool:
        """A check which only allows managers to use the command."""
        return any(role.id in self.aj_config.discord_role_manager for role in interaction.user.roles)




def _main():
    """ main function """
    # global ajdb
    # global last_hello_member

    # ajdb = None
    # last_hello_member = None

    with AjConfig(break_if_missing=True,
                  save_on_exit=False,                                 #TODO: change to True
                  file_path=Path("tests/.env")/"ajbot") as aj_config: #TODO: remove file_path arg


        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        my_app = MyAppEventsAndCommands(aj_config, intents)
        # _gdrive = GoogleDrive(aj_config)
        # ajdb = AjDb(aj_config, _gdrive.get_file(aj_config.file_id_db))


        # client = MyClient(intents=intents,
        #                   guild=discord.Object(aj_config.discord_guild))

        # # List of checks that can be used with app commands
        # # ========================================================
        # def _is_bot_owner(interaction: discord.Interaction) -> bool:
        #     """A check which only allows the bot owner to use the command."""
        #     return interaction.user.id == aj_config.discord_bot_owner


        # # List of events for the bot
        # # ========================================================
        # @client.event
        # async def on_ready():
        #     print(f'Logged in as {client.user} (ID: {client.user.id})')
        #     print('------')


        # # List of commands for the bot
        # # ========================================================
        # @client.tree.command()
        # async def hello(interaction: discord.Interaction):
        #     """Dis bonjour à l'utilisateur."""
        #     global last_hello_member
        #     if interaction.user == last_hello_member:
        #         message = "Toi encore ?\r\nT'as rien de mieux à faire ?"
        #     else:
        #         last_hello_member = interaction.user
        #         message = f'Bonjour {interaction.user.mention}!'
        #     await interaction.response.send_message(message)

        # @client.tree.command()
        # # @app_commands.checks.has_role("bureau")
        # @app_commands.checks.has_permissions(manage_roles=True)
        # @app_commands.rename(in_member='membre')
        # @app_commands.describe(in_member='Le membre à rechercher.')
        # async def membre(interaction: discord.Interaction, in_member:str):
        #     """ (Réservé au bureau) Affiche les infos des membres. Parametre = ID, pseudo discord ou nom (complet ou partiel)
        #         paramètre au choix:
        #             - ID (ex: 12, 124)
        #             - pseudo_discord (ex: VbrBot)
        #             - prénom nom ou nom prénom (sans guillement)
        #             supporte des valeurs approximatives comme
        #                 - nom ou prenom seul
        #                 - nom et/ou prénom approximatif
        #             retourne alors une liste avec la valeur de match)
        #     """
        #     global ajdb
        #     members = await ajdb.members.search(in_member, None, 50, False)

        #     if members:
        #         reply = "\r\n".join([f"{member:short}" for member in members])
        #     else:
        #         reply = f"Je connais pas ton {in_member}."

        #     await interaction.response.send_message(reply, ephemeral=True, delete_after=5)







        # @client.tree.command()
        # @app_commands.describe(
        #     first_value='The first value you want to add something to',
        #     second_value='The value you want to add to the first value',
        # )
        # async def add(interaction: discord.Interaction, first_value: int, second_value: int):
        #     """Adds two numbers together."""
        #     await interaction.response.send_message(f'{first_value} + {second_value} = {first_value + second_value}')


        # # The rename decorator allows us to change the display of the parameter on Discord.
        # # In this example, even though we use `text_to_send` in the code, the client will use `text` instead.
        # # Note that other decorators will still refer to it as `text_to_send` in the code.
        # @client.tree.command()
        # @app_commands.rename(text_to_send='text')
        # @app_commands.describe(text_to_send='Text to send in the current channel')
        # async def send(interaction: discord.Interaction, text_to_send: str):
        #     """Sends the text into the current channel."""
        #     await interaction.response.send_message(text_to_send)

        # # To make an argument optional, you can either give it a supported default argument
        # # or you can mark it as Optional from the typing standard library. This example does both.
        # @client.tree.command()
        # @app_commands.check(_is_bot_owner)
        # @app_commands.checks.has_permissions(manage_roles=True)
        # @app_commands.describe(member='The member you want to get the joined date from; defaults to the user who uses the command')
        # async def joined(interaction: discord.Interaction, member: Optional[discord.Member] = None):
        #     """Says when a member joined."""
        #     # If no member is explicitly provided then we use the command user here
        #     user = member or interaction.user

        #     # Tell the type checker that this is a Member
        #     assert isinstance(user, discord.Member)

        #     # The format_dt function formats the date time into a human readable representation in the official client
        #     # Joined at can be None in very bizarre cases so just handle that as well
        #     if user.joined_at is None:
        #         await interaction.response.send_message(f'{user} has no join date.')
        #     else:
        #         await interaction.response.send_message(f'{user} joined {discord.utils.format_dt(user.joined_at)}')

        # @joined.error
        # async def joined_error(interaction: discord.Interaction, error: app_commands.CheckFailure):
        #     await interaction.response.send_message(f'You do not have permission to use this command. ({error})', ephemeral=True)


        # # List of context menu commands for the bot
        # # ========================================================

        # # A Context Menu command is an app command that can be run on a member or on a message by
        # # accessing a menu within the client, usually via right clicking.
        # # It always takes an interaction as its first parameter and a Member or Message as its second parameter.


        # # This context menu command only works on members
        # @client.tree.context_menu(name='Show Join Date')
        # async def show_join_date(interaction: discord.Interaction, member: discord.Member):
        #     # The format_dt function formats the date time into a human readable representation in the official client
        #     # Joined at can be None in very bizarre cases so just handle that as well

        #     if member.joined_at is None:
        #         await interaction.response.send_message(f'{member} has no join date.')
        #     else:
        #         await interaction.response.send_message(f'{member} joined at {discord.utils.format_dt(member.joined_at)}',
        #                                                 ephemeral=True)


        # # This context menu command only works on messages
        # @client.tree.context_menu(name='Report to Moderators')
        # async def report_message(interaction: discord.Interaction, message: discord.Message):
        #     # We're sending this response message with ephemeral=True, so only the command executor can see it
        #     await interaction.response.send_message(
        #         f'Thanks for reporting this message by {message.author.mention} to our moderators.', ephemeral=True
        #     )

        #     # Make sure that we're inside a guild
        #     if interaction.guild is None:
        #         await interaction.response.send_message('This command can only be used in a server.', ephemeral=True)
        #         return

        #     # Handle report by sending it into a log channel
        #     log_channel = interaction.guild.get_channel(0)  # replace with your channel id

        #     if log_channel is None or not isinstance(log_channel, discord.abc.Messageable):
        #         await interaction.response.send_message('Log channel not found or not messageable.', ephemeral=True)
        #         return

        #     embed = discord.Embed(title='Reported Message')
        #     if message.content:
        #         embed.description = message.content

        #     embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        #     embed.timestamp = message.created_at

        #     url_view = discord.ui.View()
        #     url_view.add_item(discord.ui.Button(label='Go to Message', style=discord.ButtonStyle.url, url=message.jump_url))

        #     await log_channel.send(embed=embed, view=url_view)


        token = credentials.get_set_discord(aj_config,
                                            prompt_if_present=False)

        aj_config.save()  # ensure any changes are saved before running #TODO: change class to non context mgr?
        try:
            my_app.client.run(token)
        except (discord.errors.LoginFailure, CredsException):
            print("Missing or Invalid token. Please define it using either set token using 'aj_setsecret'")

    print("Bot has shutdown.")
    return 0

if __name__ == "__main__":
    sys.exit(_main())
