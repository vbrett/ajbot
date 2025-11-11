""" This example requires the 'message_content' intent.
"""
from typing import Optional
# from functools import wraps
# import tempfile
# from pathlib import Path

import discord
from discord import app_commands
# from dateparser import parse as dateparse
# from vbrpytools.dicjsontools import save_json_file

from ajbot import __version__ as ajbot_version
from ajbot._internal.ajdb import AjDb, MemberId
from ajbot._internal.exceptions import OtherException
from ajbot._internal.config import AjConfig #, DATEPARSER_CONFIG

def get_member_dict(discord_client, guild_names=None):
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
            await interaction.response.send_message(message, ephemeral=True)

        @self.client.tree.command(name="membre")
        @app_commands.check(self._is_member)
        @app_commands.rename(disc_member='pseudo')
        @app_commands.rename(int_member='id')
        @app_commands.rename(str_member='nom')
        @app_commands.describe(disc_member='pseudo discord.')
        @app_commands.describe(int_member='ID de l\'asso.')
        @app_commands.describe(str_member='nom (ID, nom complet ou partiel)')
        async def member(interaction: discord.Interaction,
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
        async def version(interaction: discord.Interaction):
            """ Affiche la version du bot
            """
            await interaction.response.send_message(f"Version du bot: {ajbot_version}", ephemeral=True)


        # # List of context menu commands for the bot
        # # ========================================================

        @self.client.tree.context_menu(name='Info membre')
        @app_commands.check(self._is_member)
        async def show_name(interaction: discord.Interaction, member: discord.Member):
            await self.send_member_info(interaction=interaction, disc_member=member)

        @self.client.tree.error
        async def error_report(interaction: discord.Interaction, exception):
            await interaction.response.send_message(f"Houla... un truc chelou c'est passé:\r\n{exception}", ephemeral=True)


    # # Support functions
    # # ========================================================

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
            members = await aj_db.search_member(input_member, 50, False)

        embed = None
        reply = f"Je ne connais pas ton ou ta {input_member}."
        if members:
            embed = discord.Embed(color=discord.Color.orange())
            format_style = "full" if self._is_manager(interaction) else "simple"
            embed.add_field(name = 'id', inline=True,
                            value = '\n'.join(str(m.member_id) for m in members)
                        )
            embed.add_field(name = 'Discord', inline=True,
                            value = '\n'.join(('@' + str(m.discord.pseudo)) if m.discord else '' for m in members)
                           )
            if members[0].match_val:
                embed.add_field(name = 'Nom (% match)', inline=True,
                                value = '\n'.join(' '.join([f'{m.credential:{format_style}}' if m.credential else '',
                                                            f'({m.match_val}%)' if m.match_val else '(100%)']) for m in members)
                            )
            else:
                embed.add_field(name = 'Nom', inline=True,
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


# class MyCommandsAndEvents(commands.Cog):
#     """ A class to hold bot commands. """
#     def __init__(self, bot,
#                  aj_config:AjConfig,
#                  export_members = None):
#         self.bot = bot
#         self.aj_config = aj_config  #TODO: maybe remove
#         self.last_hello_member = None
#         self.export_members = export_members
#         self._gdrive = GoogleDrive(aj_config)
#         aj_file = self._gdrive.get_file(aj_config.file_id_db)
#         self.ajdb = AjDb(aj_config, aj_file)

#     @commands.Cog.listener()
#     async def on_ready(self):
#         """ Appelé lors de la connexion du bot. """
#         print(f'We have logged in as {self.bot.user}')
#         brett_server, *_ = [guild for guild in self.bot.guilds if guild.name == "Brett"]
#         general_channel, *_ = [channel for channel in brett_server.channels if channel.name == "général"]
#         await general_channel.send("Bonjour, je suis en ligne.\r\nEnvoie '$help' pour savoir ce que je peux faire!")
#         if self.export_members:
#             save_json_file(get_member_dict(discord_client=self.bot), self.export_members, preserve=False)


#     @commands.command(name='roles')
#     @needs_manage_role
#     async def _roles(self, ctx):
#         """ (Réservé au bureau) Envoie un fichier JSON avec la liste des membres du serveur. """
#         with tempfile.TemporaryDirectory() as temp_dir:
#             json_filename = "members.json"
#             member_info_json_file = Path(temp_dir) / json_filename
#             save_json_file(get_member_dict(discord_client=self.bot,
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
#             reply = "\r\n".join([f"{member:full}" for member in members])
#         else:
#             reply = f"Je connais pas ton {in_member}."

#         await ctx.reply(reply)




if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
