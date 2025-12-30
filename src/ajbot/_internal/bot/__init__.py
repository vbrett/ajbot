""" Discord bot
"""
from typing import Optional
# import tempfile
# from pathlib import Path

import discord
from discord import app_commands, Interaction
# from dateparser import parse as dateparse
# from vbrpytools.dicjsontools import save_json_file

from ajbot import __version__ as ajbot_version
from ajbot._internal.config import AjConfig #, DATEPARSER_CONFIG
from ajbot._internal.ajdb import AjDb
from ajbot._internal.bot import checks, event, member, role, season, responses
from ajbot._internal.exceptions import OtherException


async def _init_bot_env():
    """
    preload in config & cache some semi-permanent data from DB
    """
    with AjConfig(save_on_exit=True) as aj_config:
        async with AjDb(aj_config=aj_config) as aj_db:
            await aj_db.init_cache()
            await aj_config.udpate_roles(aj_db=aj_db)

class MyDiscordClient(discord.Client):
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


class AjBot():
    """ class to encapsulate events and commands of the bot
    """
    client : MyDiscordClient

    def __init__(self,
                 guild,
                 intents:discord.Intents):

        self.client = MyDiscordClient(intents=intents,
                                      guild=discord.Object(guild))
        self.last_hello_member : discord.User = None
        self.last_hello_member_count : int = 0


        # ========================================================
        # List of events for the bot
        # ========================================================
        @self.client.event
        async def on_ready():
            # preload in config & cache some semi-permanent data from DB
            await _init_bot_env()

            print(f'Logged in as {self.client.user} (ID: {self.client.user.id})')
            print('------')


        # ========================================================
        # List of commands for the bot
        # ========================================================

        # General commands
        # ========================================================
        @self.client.tree.command(name="version")
        @app_commands.check(checks.is_manager)
        @app_commands.checks.cooldown(1, 5)
        async def cmd_version(interaction: Interaction):
            """ Affiche la version du bot
            """
            await responses.send_response_as_text(interaction=interaction,
                                                content=f"Version du bot: {ajbot_version}",
                                                ephemeral=True)

        @self.client.tree.command(name="maitenance")
        @app_commands.check(checks.is_owner)
        @app_commands.checks.cooldown(1, 5)
        async def cmd_maitenance(interaction: Interaction):
            """ reset ajdb cache
            """
            if not interaction.response.type:
                await interaction.response.defer(ephemeral=True,)

            await _init_bot_env()

            await responses.send_response_as_text(interaction=interaction,
                                           content="👷‍♂️ C'est tout propre !",
                                           ephemeral=True)

        @self.client.tree.command(name="bonjour")
        @app_commands.check(checks.is_member)
        @app_commands.checks.cooldown(1, 5)
        async def cmd_hello(interaction: Interaction):
            """C'est toujours bien d'être poli avec moi"""
            message_list=[f"Bonjour {interaction.user.mention} !",
                          f"Re-bonjour {interaction.user.mention} !",
                          f"Re-re-bonjour {interaction.user.mention} !",
                          "Tu insistes dis donc...",
                          "Encore ? T'as rien de mieux à faire ?",
                          "Mais lâche moi le microprocesseur !",
                          "Bon, c'est plus drôle là.",
                         ]

            self.last_hello_member_count = 0 if interaction.user != self.last_hello_member else min([self.last_hello_member_count + 1, len(message_list)-1])
            self.last_hello_member = interaction.user
            await responses.send_response_as_text(interaction=interaction,
                                           content=message_list[self.last_hello_member_count],
                                           ephemeral=True)


        # Member related commands
        # ========================================================
        @self.client.tree.command(name="membre")
        @app_commands.check(checks.is_member)
        @app_commands.checks.cooldown(1, 5)
        @app_commands.rename(disc_member='pseudo')
        @app_commands.describe(disc_member='pseudo discord')
        @app_commands.rename(int_member='id')
        @app_commands.describe(int_member='numéro de membre de l\'asso')
        @app_commands.rename(str_member='nom')
        @app_commands.describe(str_member='prénom et/ou nom (complet, partiel ou approximatif)')
        async def cmd_member(interaction: Interaction,
                             disc_member:Optional[discord.Member]=None,
                             int_member:Optional[int]=None,
                             str_member:Optional[str]=None):
            """ Affiche les infos du, de la ou des membres qui correspond(ent) le plus aux infos fournies.
            """
            async with AjDb() as aj_db:
                await member.display(aj_db=aj_db,
                                         interaction=interaction,
                                         disc_member=disc_member,
                                         int_member=int_member,
                                         str_member=str_member)

        @self.client.tree.command(name="roles")
        @app_commands.check(checks.is_manager)
        @app_commands.checks.cooldown(1, 5)
        async def cmd_roles(interaction: Interaction,):
            """ Affiche les membres qui n'ont pas le bon role
            """
            with AjConfig(save_on_exit=False) as aj_config:
                async with AjDb(aj_config=aj_config) as aj_db:
                    await role.display(aj_config=aj_config,
                                        aj_db=aj_db,
                                        interaction=interaction)


        # Events & Season related commands
        # ========================================================

        @self.client.tree.command(name="evenement")
        @app_commands.check(checks.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @app_commands.rename(event_str='évènement')
        @app_commands.describe(event_str='évènement à afficher')
        @app_commands.autocomplete(event_str=checks.AutocompleteFactory(method="query_events").ac)
        @app_commands.rename(season_name='saison')
        @app_commands.describe(season_name='la saison à afficher (aucune = saison en cours)')
        @app_commands.autocomplete(season_name=checks.AutocompleteFactory(method="query_seasons",
                                                                          attr_name='name').ac)
        async def cmd_events(interaction: Interaction,
                         event_str:Optional[str]=None,
                         season_name:Optional[str]=None,
                         ):
            """ Affiche un évènement particulier ou ceux d'une saison donnée. Aucun = crée un nouvel évènement
            """
            async with AjDb() as aj_db:
                await event.display(aj_db=aj_db,
                                    interaction=interaction,
                                    season_name=season_name,
                                    event_str=event_str)

        @self.client.tree.command(name="saison")
        @app_commands.check(checks.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @app_commands.rename(season_name='saison')
        @app_commands.describe(season_name='la saison à afficher (aucune = saison en cours)')
        @app_commands.autocomplete(season_name=checks.AutocompleteFactory(method="query_seasons",
                                                                          attr_name='name').ac)
        async def cmd_seasons(interaction: Interaction,
                              season_name:Optional[str]=None):
            """ Affiche la liste des présences & cotisants d'une saison donnée
            """
            async with AjDb() as aj_db:
                await season.display(aj_db=aj_db,
                                     interaction=interaction,
                                     season_name=season_name)


        # ========================================================
        # List of context menu commands for the bot
        # ========================================================

        @self.client.tree.context_menu(name='Info membre')
        @app_commands.check(checks.is_member)
        async def ctxt_member(interaction: Interaction, discord_member: discord.Member):
            async with AjDb() as aj_db:
                await member.display(aj_db=aj_db,
                                     interaction=interaction,
                                     disc_member=discord_member)


        # ========================================================
        # Error handling
        # =================================================

        @self.client.tree.error
        async def error_report(interaction: Interaction, exception):
            match exception:
                case app_commands.CommandOnCooldown():
                    error_message = "😵‍💫 Ouh là, tout doux le foufou, tu vas trop vite.\r\n\r\nRenvoie ta commande un peu plus tard."

                case app_commands.CheckFailure():
                    error_message = "🧙‍♂️ Désolé jeune padawan, seul un grand maître des arcanes peut effectuer cette commande."

                case _:
                    error_message =f"😱 Oups ! un truc chelou c'est passé. Relis la règle du jeu.\r\n{exception}"

            await responses.send_response_as_text(interaction=interaction, content=error_message, ephemeral=True)


if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
