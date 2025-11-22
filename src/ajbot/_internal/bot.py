""" This example requires the 'message_content' intent.
"""
from functools import wraps
from typing import Optional
# from functools import wraps
# import tempfile
# from pathlib import Path

import discord
from discord import app_commands
# from dateparser import parse as dateparse
# from vbrpytools.dicjsontools import save_json_file

from ajbot import __version__ as ajbot_version
from ajbot._internal.ajdb import AjDb
from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal.exceptions import AjBotException, OtherException
from ajbot._internal.config import AjConfig, FormatTypes #, DATEPARSER_CONFIG




def _command_season_param(func):
    """ Decorator to handle command season parameter (with autocomplete)
    """
    class _SeasonAutocomplete():
        """ Season parameter autocomplete function factory
        """
        def __init__(self):
            self._season_names = []

        def reset(self):
            """ Reset the season list for next command
            """
            self._season_names = []

        async def ac(self,
                    _interaction: discord.Interaction,
                    current: str,
                    ) -> list[app_commands.Choice[str]]:
            """ return list of season names for auto completion
            """
            if not self._season_names:
                async with AjDb() as aj_db:
                    seasons = await aj_db.query_table_content(ajdb_t.Season)
                self._season_names = [season.name for season in seasons]

            return [
                app_commands.Choice(name=season_name, value=season_name)
                for season_name in self._season_names if current.lower() in season_name.lower()
            ]

    _season_autocomplete = _SeasonAutocomplete()

    @wraps(func)
    @app_commands.rename(season_name='saison')
    @app_commands.describe(season_name='la saison à analyser (aucune = saison en cours)')
    @app_commands.autocomplete(season_name=_season_autocomplete.ac)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        _season_autocomplete.reset()
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
                 aj_config:AjConfig,
                 intents:discord.Intents):

        self.aj_config = aj_config
        self.client = MyDiscordClient(intents=intents,
                                      guild=discord.Object(aj_config.discord_guild))
        self.last_hello_member : discord.User = None
        self.last_hello_member_count : int = 0

        self.season_names = None

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
            message_list=[f"Bonjour {interaction.user.mention} !",
                          f"Re-bonjour {interaction.user.mention} !",
                          f"Re-re-bonjour {interaction.user.mention} !",
                          "...tu insistes dis donc...",
                          "Encore ? Franchement, t'as rien de mieux à faire ?",
                          "Allez, sérieux, tu veux pas lâcher ton écran ?",
                          "Mais lâche moi le microprocesseur !",
                          "Bon, c'est plus drôle là.",
                         ]

            self.last_hello_member_count = 0 if interaction.user != self.last_hello_member else min([self.last_hello_member_count + 1, len(message_list)-1])
            self.last_hello_member = interaction.user
            await interaction.response.send_message(message_list[self.last_hello_member_count], ephemeral=True)

        @self.client.tree.command(name="info_membre")
        @app_commands.check(self._is_member)
        @app_commands.rename(disc_member='pseudo')
        @app_commands.rename(int_member='id')
        @app_commands.rename(str_member='nom')
        @app_commands.describe(disc_member='pseudo discord.')
        @app_commands.describe(int_member='ID de l\'asso.')
        @app_commands.describe(str_member='nom (ID, nom complet ou partiel)')
        @app_commands.checks.cooldown(1, 5)
        async def member_info(interaction: discord.Interaction,
                              disc_member:Optional[discord.Member]=None,
                              int_member:Optional[int]=None,
                              str_member:Optional[str]=None):
            """ Affiche les infos des membres. Parametre = ID, pseudo discord ou nom (complet ou partiel)
                paramètre au choix:
                    - pseudo_discord (ex: VbrBot)
                    - ID de l'asso (ex: 12, 124)
                    - prénom nom ou nom prénom (sans guillement)
                    supporte des valeurs approximatives comme
                        - nom ou prenom seul
                        - nom et/ou prénom approximatif
                    retourne alors une liste avec la valeur de match
            """
            await self.send_member_info(interaction=interaction,
                                        disc_member=disc_member,
                                        int_member=int_member,
                                        str_member=str_member)


        @self.client.tree.command(name="version")
        @app_commands.check(self._is_manager)
        @app_commands.checks.cooldown(1, 5)
        async def version(interaction: discord.Interaction):
            """ Affiche la version du bot
            """
            await interaction.response.send_message(f"Version du bot: {ajbot_version}", ephemeral=True)




        @self.client.tree.command(name="cotisants")
        @app_commands.check(self._is_manager)
        @app_commands.checks.cooldown(1, 5)
        @_command_season_param
        async def memberships(interaction: discord.Interaction,
                              season_name:Optional[str]=None):
            """ Affiche les cotisants
            """
            async with AjDb() as aj_db:
                members = await aj_db.query_members_per_presence(season_name, subscriber_only=True)

            if members:
                if season_name:
                    summary = f"{len(members)} personne(s) ont cotisé à la saison {season_name} :"
                else:
                    summary = f"{len(members)} personne(s) ont déjà cotisé à cette saison :"

                format_style = FormatTypes.FULLSIMPLE if self._is_manager(interaction) else FormatTypes.RESTRICTED
                reply = '- ' + '\n- '.join(f'{m:{format_style}}' for m in members)
            else:
                summary = "Mais il n'y a eu personne cette saison ;-("
                reply = '---'

            # await self.send_response_basic(interaction, content=reply, ephemeral=True, split_on_eol=True)
            await self.send_response_view(interaction=interaction, title="Cotisants", summary=summary, content=reply, ephemeral=True)




        @self.client.tree.command(name="evenements")
        @app_commands.check(self._is_manager)
        @app_commands.checks.cooldown(1, 5)
        @_command_season_param
        async def events(interaction: discord.Interaction,
                         season_name:Optional[str]=None,
                         ):
            """ Affiche les evenements
            """
            async with AjDb() as aj_db:
                events = await aj_db.query_events(season_name)

            if events:
                if season_name:
                    summary = f"Il y a eu {len(events)} évènement(s) lors de la saison {season_name} :"
                else:
                    summary = f"Il y a déjà eu {len(events)} évènement(s) lors de cette saison :"

                format_style = FormatTypes.FULLSIMPLE if self._is_manager(interaction) else FormatTypes.RESTRICTED
                reply = '- ' + '\n- '.join(f'{e:{format_style}}' for e in events)
            else:
                summary = "Mais il n'y a eu aucun évènement cette saison ;-("
                reply = '---'

            # await self.send_response_basic(interaction, content=reply, ephemeral=True, split_on_eol=True)
            await self.send_response_view(interaction=interaction, title="Evènements", summary=summary, content=reply, ephemeral=True)




        @self.client.tree.command(name="presence")
        @app_commands.check(self._is_manager)
        @app_commands.checks.cooldown(1, 5)
        @_command_season_param
        async def presence(interaction: discord.Interaction,
                           season_name:Optional[str]=None,
                           ):
            """ Affiche les personne ayant participé à une saison
            """
            async with AjDb() as aj_db:
                members = await aj_db.query_members_per_presence(season_name)

            if members:
                members.sort(key=lambda x: x, reverse=False)
                if season_name:
                    summary = f"{len(members)} personne(s) sont venus lors de la saison {season_name} :"
                else:
                    summary = f"{len(members)} personne(s) sont déjà venus lors de cette saison :"

                format_style = FormatTypes.FULLSIMPLE if self._is_manager(interaction) else FormatTypes.RESTRICTED
                reply = '- ' + '\n- '.join(f'{m:{format_style}} - {m.season_presence_count(season_name)} participation(s)' for m in members)
            else:
                summary = "Mais il n'y a eu personne cette saison ;-("
                reply = "---"

            # await self.send_response_basic(interaction, content=content, ephemeral=True, split_on_eol=True)
            await self.send_response_view(interaction=interaction, title="Présence", summary=summary, content=reply, ephemeral=True)
            self.season_names = None


        # # List of context menu commands for the bot
        # # ========================================================

        @self.client.tree.context_menu(name='Info membre')
        @app_commands.check(self._is_member)
        async def show_name(interaction: discord.Interaction, member: discord.Member):
            await self.send_member_info(interaction=interaction, disc_member=member)

        @self.client.tree.error
        async def error_report(interaction: discord.Interaction, exception):
            if isinstance(exception, app_commands.CommandOnCooldown):
                error_message = "Oh la! tout doux les foufous...\r\nRenvoie ta commande un peu plus tard."
            else:
                error_message =f"Houla... un truc chelou c'est passé:\r\n{exception}"

            await interaction.response.send_message(error_message, ephemeral=True)
            self.season_names = None

    # # Support functions
    # # ========================================================
    async def send_response_basic(self, interaction: discord.Interaction, content:str, ephemeral=False,
                                  chunk_size=1800, split_on_eol=True):
        """ Send basic command response, handling splitting it if needed (limit = 2000 characters).
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
                await interaction.response.send_message(chunk, ephemeral=ephemeral)
                first_answer = False
            else:
                await interaction.followup.send('(...)\n' + chunk, ephemeral=ephemeral)

    async def send_response_view(self, interaction: discord.Interaction,
                                 title:str, summary:str, content:str,
                                 ephemeral=False,):
        """ Send command response as a view
        """
        view = discord.ui.LayoutView()
        container = discord.ui.Container()
        view.add_item(container)

        container.add_item(discord.ui.TextDisplay(f'# __{title}__'))
        container.add_item(discord.ui.TextDisplay(f'## {summary}'))
        container.add_item(discord.ui.TextDisplay(f'>>> {content}'))

        timestamp = discord.utils.format_dt(interaction.created_at, 'F')
        footer = discord.ui.TextDisplay(f'-# Généré par {interaction.user} (ID: {interaction.user.id}) | {timestamp}')

        container.add_item(footer)
        await interaction.response.send_message(view=view, ephemeral=ephemeral)


    async def send_member_info(self, interaction: discord.Interaction,
                               disc_member:discord.Member=None,
                               int_member:int=None,
                               str_member:str=None,
                               delete_after=None):
        """ Affiche les infos des membres
        """
        input_member = [x for x in [disc_member, str_member, int_member] if x is not None]
        if len(input_member) != 1:
            await interaction.response.send_message("Tu peux fournir soit:\r\n* un pseudo\r\n* un nom\r\n* un ID\r\nMais s'il te plait, pas de mélange, c'est pas bon pour ma santé.",
                                                    ephemeral=True, delete_after=10)
            return
        input_member = input_member[0]

        async with AjDb() as aj_db:
            members = await aj_db.query_members_per_id_info(input_member, 50, False)

        embed = None
        reply = f"Je ne connais pas ton ou ta {input_member}."
        if members:
            is_self = len(members) == 1 and members[0].discord_pseudo.name == interaction.user.name
            embed = discord.Embed(color=discord.Color.orange())
            format_style = FormatTypes.FULLSIMPLE if (is_self or self._is_manager(interaction)) else FormatTypes.RESTRICTED
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

        await interaction.response.send_message(reply, embed=embed, ephemeral=True, delete_after=delete_after)


    # List of checks that can be used with app commands
    # ========================================================
    def _is_bot_owner(self, interaction: discord.Interaction) -> bool:
        """A check which only allows the bot owner to use the command."""
        return interaction.user.id == self.aj_config.discord_bot_owner

    def _is_member(self, interaction: discord.Interaction) -> bool:
        """A check which only allows members to use the command."""
        return any(role.id in self.aj_config.discord_role_member for role in interaction.user.roles)

    def _is_manager(self, interaction: discord.Interaction) -> bool:
        """A check which only allows managers to use the command."""
        return any(role.id in self.aj_config.discord_role_manager for role in interaction.user.roles)


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

#     @commands.command(name='seance')
#     @needs_aj_manage_role
#     async def _session(self, ctx, *, raw_input_date=None):
#         """ (Réservé au bureau) Affiche le nombre de présent à une seance. Parametre = date. Si vide, prend la dernière séance enregistrée """
#         session_dates = [s.date for s in self.ajdb.events.get_in_season_events(AjEvent.EVENT_TYPE_PRESENCE)]

#         if not raw_input_date:
#             input_date = max(session_dates)
#         else:
#             try:
#                 input_date = AjDate(dateparse(raw_input_date, settings=DATEPARSER_CONFIG))
#             except TypeError:
#                 input_date = None

#         if input_date:
#             # look for closest date with presence
#             session_date = min(session_dates, key=lambda x: abs(x - input_date))

#             if session_date:
#                 reply = f"Il y a eu {len([s_date for s_date in session_dates if s_date == session_date])} participants à la séance du {session_date}."
#             else:
#                 reply = f"Déso, pas trouvé de séance à la date du {raw_input_date} ou proche de cette date."
#         else:
#             reply = f"Mmmm... Ca m'étonnerait que '{raw_input_date}' soit une date."

#         await ctx.reply(reply)

#     @commands.command(name='membre')
#     @needs_aj_manage_role
#     async def _member(self, ctx, *, in_member):
#         """ (Réservé au bureau) Affiche les infos des membres. Parametre = ID, pseudo discord ou nom (complet ou partiel)
#             paramètre au choix:
#                 - ID (ex: 12, 124)
#                 - pseudo_discord (ex: VbrBot)
#                 - prénom nom ou nom prénom (sans guillement)
#                   supporte des valeurs approximatives comme
#                     - nom ou prenom seul
#                     - nom et/ou prénom approximatif
#                   retourne alors une liste avec la valeur de match)
#         """
#         members = await self.ajdb.members.search(in_member, ctx, 50, False)

#         if members:
#             reply = "\r\n".join([f"{member:{FORMAT_FULL}}" for member in members])
#         else:
#             reply = f"Je connais pas ton {in_member}."

#         await ctx.reply(reply)




if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
