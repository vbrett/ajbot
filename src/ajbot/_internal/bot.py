""" Discord bot
"""
from typing import Optional
# import tempfile
# from pathlib import Path

import discord
from discord import app_commands, Interaction
# from dateparser import parse as dateparse
# from vbrpytools.dicjsontools import save_json_file

from sqlalchemy import orm

from ajbot import __version__ as ajbot_version
from ajbot._internal.config import FormatTypes #, DATEPARSER_CONFIG
from ajbot._internal.ajdb import AjDb
from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal import bot_in, bot_out
from ajbot._internal.exceptions import OtherException

# def get_discord_members(discord_client, guild_names=None):
#     """ Returns a dictionary of members info from a list of discord guilds.
#         guilds: list of guild names to include members from.
#                 If None, all guilds the bot is in are used.
#     """
#     return {"date": discord.utils.utcnow().isoformat(),
#             "members": {guild.name: {member.id: {
#                                                 'name': member.name,
#                                                 'disp_name': member.display_name,
#                                                 'joined_at': member.joined_at.isoformat(),
#                                                 'roles': [role.name for role in member.roles]
#                                                 }
#                                     for member in guild.members}
#                         for guild in discord_client.guilds
#                         if guild_names is None or guild.name in guild_names}
#             }

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
            print(f'Logged in as {self.client.user} (ID: {self.client.user.id})')
            print('------')


        # ========================================================
        # List of commands for the bot
        # ========================================================

        # General commands
        # ========================================================
        @self.client.tree.command(name="version")
        @app_commands.check(bot_in.is_manager)
        @app_commands.checks.cooldown(1, 5)
        async def version(interaction: Interaction):
            """ Affiche la version du bot
            """
            await bot_out.send_response_as_text(interaction=interaction,
                                                content=f"Version du bot: {ajbot_version}",
                                                ephemeral=True)

        @self.client.tree.command(name="bonjour")
        @app_commands.check(bot_in.is_member)
        @app_commands.checks.cooldown(1, 5)
        async def hello(interaction: Interaction):
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
            await bot_out.send_response_as_text(interaction=interaction,
                                           content=message_list[self.last_hello_member_count],
                                           ephemeral=True)


        # Member related commands
        # ========================================================
        @self.client.tree.command(name="qui-est-ce")
        @app_commands.check(bot_in.is_member)
        @app_commands.checks.cooldown(1, 5)
        @app_commands.rename(disc_member='pseudo')
        @app_commands.describe(disc_member='pseudo discord')
        @app_commands.rename(int_member='id')
        @app_commands.describe(int_member='numéro de membre de l\'asso')
        @app_commands.rename(str_member='nom')
        @app_commands.describe(str_member='prénom et/ou nom (complet, partiel ou approximatif)')
        async def who(interaction: Interaction,
                      disc_member:Optional[discord.Member]=None,
                      int_member:Optional[int]=None,
                      str_member:Optional[str]=None):
            """ Retrouve l'identité d'un membre. Retourne le, la ou les membres qui correspond(ent) le plus aux infos fournies.
            """
            async with AjDb() as aj_db:
                await bot_out.display_member(aj_db=aj_db,
                                             interaction=interaction,
                                             disc_member=disc_member,
                                             int_member=int_member,
                                             str_member=str_member)

        @self.client.tree.command(name="roles")
        @app_commands.check(bot_in.is_manager)
        @app_commands.checks.cooldown(1, 5)
        async def roles(interaction: Interaction,):
            """ Affiche les membres qui n'ont pas le bon role
            """
            if not interaction.response.type:
                await interaction.response.defer(ephemeral=True,)

            async with AjDb() as aj_db:
                discord_wrong_roles = {}
                aj_discord = await aj_db.query_table_content(ajdb_t.DiscordPseudo)

                for discord_member in interaction.guild.members:
                    matched_members = [d.member for d in aj_discord if d.name == discord_member.name]

                    assert (len(matched_members) <= 1), f"Plusieurs membres AJDB correspondent au pseudo Discord {discord_member} !"
                    if len(matched_members) == 0:
                        if discord_member.roles:
                            discord_wrong_roles[discord_member.name] = {'expected': None,
                                                                        'actual': ','.join(r.name for r in discord_member.roles if r.name != "@everyone"),
                                                                        }


                    # if not member.bot:
                    #     db_member = await aj_db.get_member_by_discord_id(member.id)
                    #     if db_member:
                    #         if db_member in subscribers:
                    #             # Should have the subscriber role
                    #             if not bot_in.has_subscriber_role(member):
                    #                 await bot_out.add_subscriber_role(interaction=interaction,
                    #                                                   discord_member=member)
                    #         else:
                    #             # Should not have the subscriber role
                    #             if bot_in.has_subscriber_role(member):
                    #                 await bot_out.remove_subscriber_role(interaction=interaction,
                    #                                                      discord_member=member)


                await bot_out.send_response_as_text(interaction=interaction, content=str(discord_wrong_roles), ephemeral=True)


        # Season related commands
        # ========================================================

        @self.client.tree.command(name="cotisants")
        @app_commands.check(bot_in.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @app_commands.rename(season_name='saison')
        @app_commands.describe(season_name='la saison à afficher (aucune = saison en cours)')
        @app_commands.autocomplete(season_name=bot_in.AutocompleteFactory(table_class=ajdb_t.Season,
                                                                          options=[orm.lazyload(ajdb_t.Season.events), orm.lazyload(ajdb_t.Season.memberships)],
                                                                          attr_name='name').ac)
        async def memberships(interaction: Interaction,
                              season_name:Optional[str]=None):
            """ Affiche la liste des cotisants d'une saison donnée
            """
            async with AjDb() as aj_db:
                members = await aj_db.query_members_per_season_presence(season_name, subscriber_only=True)

                if members:
                    if season_name:
                        summary = f"{len(members)} personne(s) ont cotisé à la saison {season_name} :"
                    else:
                        summary = f"{len(members)} personne(s) ont déjà cotisé à cette saison :"

                    format_style = FormatTypes.FULLSIMPLE if bot_in.is_manager(interaction) else FormatTypes.RESTRICTED
                    reply = '- ' + '\n- '.join(f'{m:{format_style}}' for m in members)
                else:
                    summary = "Mais il n'y a eu personne cette saison ;-("
                    reply = '---'

                await bot_out.send_response_as_view(interaction=interaction, title="Cotisants", summary=summary, content=reply, ephemeral=True)

        @self.client.tree.command(name="evenement")
        @app_commands.check(bot_in.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @app_commands.rename(event_str='évènement')
        @app_commands.describe(event_str='évènement à afficher')
        @app_commands.autocomplete(event_str=bot_in.AutocompleteFactory(table_class=ajdb_t.Event,
                                                                        options=[orm.lazyload(ajdb_t.Event.members), orm.lazyload(ajdb_t.Event.season)]).ac)
        @app_commands.rename(season_name='saison')
        @app_commands.describe(season_name='la saison à afficher (aucune = saison en cours)')
        @app_commands.autocomplete(season_name=bot_in.AutocompleteFactory(table_class=ajdb_t.Season,
                                                                          options=[orm.lazyload(ajdb_t.Season.events), orm.lazyload(ajdb_t.Season.memberships)],
                                                                          attr_name='name').ac)
        async def events(interaction: Interaction,
                         event_str:Optional[str]=None,
                         season_name:Optional[str]=None,
                         ):
            """ Affiche un évènement particulier ou ceux d'une saison donnée. Aucun = crée un nouvel évènement
            """
            async with AjDb() as aj_db:
                await bot_out.display_event(aj_db=aj_db,
                                            interaction=interaction,
                                            season_name=season_name,
                                            event_str=event_str)

        @self.client.tree.command(name="presence")
        @app_commands.check(bot_in.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @app_commands.rename(season_name='saison')
        @app_commands.describe(season_name='la saison à afficher (aucune = saison en cours)')
        @app_commands.autocomplete(season_name=bot_in.AutocompleteFactory(table_class=ajdb_t.Season,
                                                                          options=[orm.lazyload(ajdb_t.Season.events), orm.lazyload(ajdb_t.Season.memberships)],
                                                                          attr_name='name').ac)
        async def presence(interaction: Interaction,
                           season_name:Optional[str]=None,
                           ):
            """ Affiche les personnes ayant participé à une saison donnée
            """
            async with AjDb() as aj_db:
                members = await aj_db.query_members_per_season_presence(season_name)

                if members:
                    members.sort(key=lambda x: x, reverse=False)
                    if season_name:
                        summary = f"{len(members)} personne(s) sont venus lors de la saison {season_name} :"
                    else:
                        summary = f"{len(members)} personne(s) sont déjà venus lors de cette saison :"

                    format_style = FormatTypes.FULLSIMPLE if bot_in.is_manager(interaction) else FormatTypes.RESTRICTED
                    reply = '- ' + '\n- '.join(f'{m:{format_style}} - {m.season_presence_count(season_name)} participation(s)' for m in members)
                else:
                    summary = "Mais il n'y a eu personne cette saison ;-("
                    reply = "---"

                await bot_out.send_response_as_view(interaction=interaction, title="Présence", summary=summary, content=reply, ephemeral=True)


        # ========================================================
        # List of context menu commands for the bot
        # ========================================================

        @self.client.tree.context_menu(name='Info membre')
        @app_commands.check(bot_in.is_member)
        async def show_name(interaction: Interaction, member: discord.Member):
            async with AjDb() as aj_db:
                await bot_out.display_member(aj_db=aj_db,
                                             interaction=interaction,
                                             disc_member=member)


        # ========================================================
        # Error handling
        # =================================================

        @self.client.tree.error
        async def error_report(interaction: Interaction, exception):
            if isinstance(exception, app_commands.CommandOnCooldown):
                error_message = "😵‍💫 Ouh là, tout doux le foufou, tu vas trop vite pour moi .\r\n\r\nRenvoie ta commande un peu plus tard."
            else:
                error_message =f"😱 Oups ! un truc chelou c'est passé.\r\n{exception}"

            await bot_out.send_response_as_text(interaction=interaction, content=error_message, ephemeral=True)


#     @commands.command(name='roles')
#     @needs_manage_role
#     async def _roles(self, ctx):
#         """ (Réservé au bureau) Envoie un fichier JSON avec la liste des membres du serveur. """
#         with tempfile.TemporaryDirectory() as temp_dir:
#             json_filename = "members.json"
#             member_info_json_file = Path(temp_dir) / json_filename
#             save_json_file(get_discord_members(discord_client=self.bot,
#                                         guild_names=([ctx.guild.name] if ctx.guild else None)),
#                         member_info_json_file, preserve=False)
#             await ctx.reply("Et voilà:",
#                             file=discord.File(fp=member_info_json_file,
#                                             filename=json_filename))

#     # @commands.command(name='emargement')
#     # @needs_administrator
#     # async def _signsheet(self, ctx):
#     #     """ (Réservé au bureau) Envoie la fiche d'émargement. """
#     #     sign_sheet_filename="emargement.pdf"
#     #     with self._gdrive.get_file(aj_config.file_id_presence) as sign_sheet:
#     #         # with tempfile.TemporaryDirectory() as temp_dir:
#     #         #     sign_sheet_file = Path(temp_dir) / sign_sheet_filename
#     #         #     try:
#     #         #         with open(sign_sheet_file, mode="wb") as fp:
#     #         #             fp.write(sign_sheet)
#     #         #         await ctx.reply("Et voilà:",
#     #         #                         file=discord.File(fp=sign_sheet_file,
#     #         #                                         filename=sign_sheet_filename))
#     #         #     except Exception as e:
#     #         #         print(e)
#     #         #         raise
#     #         await ctx.reply("Et voilà:",
#     #                         file=discord.File(fp=sign_sheet,
#     #                                         filename=sign_sheet_filename))


if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
