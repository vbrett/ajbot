""" This example requires the 'message_content' intent.
"""
import sys
from typing import Optional
from functools import wraps
import tempfile
from pathlib import Path

import discord
from discord import app_commands
from dateparser import parse as dateparse
from vbrpytools.dicjsontools import save_json_file

from ajbot import credentials
from ajbot._internal.ajdb import AjDb, AjDate, AjEvent
from ajbot._internal.exceptions import CredsException
from ajbot._internal.google_api import GoogleDrive
from ajbot._internal.config import DATEPARSER_CONFIG, AjConfig

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

        _gdrive = GoogleDrive(aj_config)
        self.aj_db = AjDb(aj_config, _gdrive.get_file(aj_config.file_id_db))

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



# def needs_manage_role(func):
#     """ A decorator to protect commands that require manage role permission. """
#     @wraps(func)
#     async def wrapper(self, ctx, *args, **kwargs):
#         if not ctx.author.guild_permissions.manage_roles:
#             await ctx.reply("Tu dois avoir la permission 'Gérer les rôles' pour pouvoir utiliser cette commande.")
#             return
#         return await func(self, ctx, *args, **kwargs)
#     return wrapper

# def needs_administrator(func):
#     """ A decorator to protect commands that require administrator permissions. """
#     @wraps(func)
#     async def wrapper(self, ctx, *args, **kwargs):
#         if not ctx.author.guild_permissions.administrator:
#             await ctx.reply("Tu dois être administrateur pour pouvoir utiliser cette commande.")
#             return
#         return await func(self, ctx, *args, **kwargs)
#     return wrapper

# def needs_aj_manage_role(func):
#     """ A decorator to protect commands that require manage role permission on the AJ server. """
#     @wraps(func)
#     @needs_manage_role
#     async def wrapper(self, ctx, *args, **kwargs):
#         #FIXME replace with proper call
#         if ctx.guild.id != self.aj_config.discord_guild:
#             await ctx.reply("Cette commande n'est pas possible depuis ce serveur.")
#             return
#         return await func(self, ctx, *args, **kwargs)
#     return wrapper


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


#     @commands.command(name='hello')
#     async def _hello(self, ctx):
#         """ Dis bonjour à l'utilisateur. """
#         if ctx.author == self.last_hello_member:
#             message = "Toi encore ?\r\nT'as rien de mieux à faire ?"
#         else:
#             self.last_hello_member = ctx.author
#             message = f'Bonjour {ctx.author.display_name}!'

#         await ctx.reply(message)

#     @commands.command(name='test')
#     @needs_administrator
#     async def _test(self, ctx, *args):
#         """ (Réservé aux admin) Commande de test qui renvoie les arguments. """
#         await ctx.reply(" - ".join(args))

#     @commands.command(name='bye')
#     @needs_administrator
#     async def _bye(self, ctx):
#         """ (Réservé aux admin) Déconnecte le bot. """
#         await ctx.reply("J'me déconnecte. Bye!")
#         await self.bot.close()

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
#             reply = "\r\n".join([f"{member:manager}" for member in members])
#         else:
#             reply = f"Je connais pas ton {in_member}."

#         await ctx.reply(reply)



def _main():
    """ main function """
    with AjConfig(break_if_missing=True,
                  save_on_exit=True) as aj_config:


        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        my_app = MyAppEventsAndCommands(aj_config, intents)

        token = credentials.get_set_discord(aj_config,
                                            prompt_if_present=False)

        # ensure any changes are saved before running
        aj_config.save()  #TODO: change class to non context mgr?
        try:
            my_app.client.run(token)
        except (discord.errors.LoginFailure, CredsException):
            print("Missing or Invalid token. Please define it using either set token using 'aj_setsecret'")

    print("Bot has shutdown.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
