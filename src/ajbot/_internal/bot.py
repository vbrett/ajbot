""" Discord bot
"""
from typing import Optional, cast
from datetime import datetime, timedelta
# import tempfile
# from pathlib import Path

import discord
from discord import app_commands, Interaction
# from dateparser import parse as dateparse
# from vbrpytools.dicjsontools import save_json_file

from ajbot import __version__ as ajbot_version
from ajbot._internal.config import AjConfig, FormatTypes #, DATEPARSER_CONFIG
from ajbot._internal.ajdb import AjDb
from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal import bot_in, bot_out
from ajbot._internal.exceptions import OtherException


async def _init_env():
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
            await _init_env()

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

        @self.client.tree.command(name="maitenance")
        @app_commands.check(bot_in.is_owner)
        @app_commands.checks.cooldown(1, 5)
        async def maitenance(interaction: Interaction):
            """ reset ajdb cache
            """
            if not interaction.response.type:
                await interaction.response.defer(ephemeral=True,)

            await _init_env()

            await bot_out.send_response_as_text(interaction=interaction,
                                           content="👷‍♂️ C'est tout propre !",
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

            with AjConfig(save_on_exit=True) as aj_config:
                async with AjDb(aj_config=aj_config) as aj_db:
                    discord_role_mismatches = {}
                    aj_members = await aj_db.query_table_content(ajdb_t.Member)
                    aj_discord_roles = await aj_db.query_table_content(ajdb_t.DiscordRole)
                    default_asso_role_id = aj_config.asso_member_default
                    default_discord_role_ids = [dr.id for dr in aj_discord_roles if default_asso_role_id in [ar.id for ar in cast(ajdb_t.DiscordRole, dr).asso_roles]]

                    for discord_member in interaction.guild.members:
                        actual_role_ids = [r.id for r in discord_member.roles if r.name != "@everyone"]

                        matched_members = [cast(ajdb_t.Member, d) for d in aj_members if d.discord_pseudo and d.discord_pseudo.name == discord_member.name]
                        assert (len(matched_members) <= 1), f"Erreur dans la DB: Plusieurs membres correspondent au même pseudo Discord {discord_member}:\n{', '.join(m.name for m in matched_members)}"
                        if len(matched_members) == 0:
                            member = None
                            # discord user not found in db, expected discord role is default
                            expected_role_ids = default_discord_role_ids
                        else:
                            # discord user found in db, check using asso role
                            member = matched_members[0]
                            if (not member.is_subscriber
                                and member.is_past_subscriber
                                and (   not member.last_presence
                                     or member.last_presence < (datetime.now().date() - timedelta(days = aj_config.asso_role_reset_duration_days)))):
                                # user is a past subscriber but has not participated for some time, expected discord role is default
                                expected_role_ids = default_discord_role_ids
                            else:
                                # expected discord role(s) are the ones mapped to user asso role
                                expected_role_ids = [dr.id for dr in cast(ajdb_t.AssoRole, member.current_asso_role).discord_roles]

                        expected_role_ids = set(expected_role_ids)
                        actual_role_ids = set(actual_role_ids)
                        if expected_role_ids != actual_role_ids:
                            expected_role_key = '; '.join(f"{interaction.guild.get_role(id) or id}" for id in expected_role_ids)
                            discord_role_mismatches.setdefault(expected_role_key, [])
                            discord_role_mismatches[expected_role_key].append(  f"{member if member else discord_member.name} - "
                                                                                + '; '.join(f"{interaction.guild.get_role(id) or id}" for id in actual_role_ids))

                    if discord_role_mismatches:
                        summary = "Des roles ne sont pas correctements attribués :"
                        reply = '\n'.join(f"- Attendu(s): {k}\n  - {'\n  - '.join(e for e in v)}" for k, v in discord_role_mismatches.items())
                        # reply = '\n'.join(f"- {u['who']} :\n  - attendu(s): {u['expected']}\n  - actuel(s): {u['actual']}" for u in discord_role_mismatches)
                    else:
                        summary = "Parfait ! Tout le monde a le bon rôle !"
                        reply = None

                    await bot_out.send_response_as_view(interaction=interaction, title="Rôles", summary=summary, content=reply, ephemeral=True)


        # Season related commands
        # ========================================================

        @self.client.tree.command(name="evenement")
        @app_commands.check(bot_in.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @app_commands.rename(event_str='évènement')
        @app_commands.describe(event_str='évènement à afficher')
        @app_commands.autocomplete(event_str=bot_in.AutocompleteFactory(method="query_events").ac)
        @app_commands.rename(season_name='saison')
        @app_commands.describe(season_name='la saison à afficher (aucune = saison en cours)')
        @app_commands.autocomplete(season_name=bot_in.AutocompleteFactory(method="query_seasons",
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

        @self.client.tree.command(name="saison")
        @app_commands.check(bot_in.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @app_commands.rename(season_name='saison')
        @app_commands.describe(season_name='la saison à afficher (aucune = saison en cours)')
        @app_commands.autocomplete(season_name=bot_in.AutocompleteFactory(method="query_seasons",
                                                                          attr_name='name').ac)
        async def memberships(interaction: Interaction,
                              season_name:Optional[str]=None):
            """ Affiche la liste des présences & cotisants d'une saison donnée
            """
            async with AjDb() as aj_db:
                participants = await aj_db.query_members_per_season_presence(season_name)
                subscribers = await aj_db.query_members_per_season_presence(season_name, subscriber_only=True)
                format_style = FormatTypes.FULLSIMPLE if bot_in.is_manager(interaction) else FormatTypes.RESTRICTED

                if participants:
                    summary = f"{len(participants)} personne(s) sont venues et {len(subscribers)} ont cotisé :"

                    reply = '- ' + '\n- '.join(f'{m:{format_style}} - **{m.season_presence_count(season_name)}** participation(s) -' + (' ___non___' if m not in subscribers else '') +' cotisant' for m in participants)
                else:
                    if subscribers:
                        summary = f"Je ne sais pas combien de personne sont venues, mais {len(subscribers)} ont cotisé :"
                        reply = '- ' + '\n- '.join(f'{m:{format_style}}' for m in subscribers)
                    else:
                        summary = "😱 Mais il n'y a eu personne ! 😱"
                        reply = '---'

                await bot_out.send_response_as_view(interaction=interaction,
                                                    title=f"Saison {season_name if season_name else 'en cours'}",
                                                    summary=summary,
                                                    content=reply,
                                                    ephemeral=True)


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
            match exception:
                case app_commands.CommandOnCooldown():
                    error_message = "😵‍💫 Ouh là, tout doux le foufou, tu vas trop vite pour moi .\r\n\r\nRenvoie ta commande un peu plus tard."

                case app_commands.CheckFailure():
                    error_message = "🧙‍♂️ Désolé jeune padawan, seul un grand maître des arcanes peut effectuer cette commande."

                case _:
                    error_message =f"😱 Oups ! un truc chelou c'est passé. Relis la règle du jeu.\r\n{exception}"

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
