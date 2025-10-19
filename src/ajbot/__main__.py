""" This example requires the 'message_content' intent.
"""
import sys
import asyncio
from functools import wraps
import tempfile
from pathlib import Path

import discord
from discord.ext import commands
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


def needs_manage_role(func):
    """ A decorator to protect commands that require manage role permission. """
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        if not ctx.author.guild_permissions.manage_roles:
            await ctx.reply("Tu dois avoir la permission 'Gérer les rôles' pour pouvoir utiliser cette commande.")
            return
        return await func(self, ctx, *args, **kwargs)
    return wrapper

def needs_administrator(func):
    """ A decorator to protect commands that require administrator permissions. """
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        if not ctx.author.guild_permissions.administrator:
            await ctx.reply("Tu dois être administrateur pour pouvoir utiliser cette commande.")
            return
        return await func(self, ctx, *args, **kwargs)
    return wrapper

def needs_aj_manage_role(func):
    """ A decorator to protect commands that require manage role permission on the AJ server. """
    @wraps(func)
    @needs_manage_role
    async def wrapper(self, ctx, *args, **kwargs):
        #FIXME replace with proper call
        if ctx.guild.id != self.aj_config.discord_guild:
            await ctx.reply("Cette commande n'est pas possible depuis ce serveur.")
            return
        return await func(self, ctx, *args, **kwargs)
    return wrapper


class MyCommandsAndEvents(commands.Cog):
    """ A class to hold bot commands. """
    def __init__(self, bot,
                 aj_config:AjConfig,
                 export_members = None):
        self.bot = bot
        self.aj_config = aj_config  #TODO: maybe remove
        self.last_hello_member = None
        self.export_members = export_members
        self._gdrive = GoogleDrive(aj_config)
        aj_file = self._gdrive.get_file(aj_config.file_id_db)
        self.ajdb = AjDb(aj_config, aj_file)

    @commands.Cog.listener()
    async def on_ready(self):
        """ Appelé lors de la connexion du bot. """
        print(f'We have logged in as {self.bot.user}')
        brett_server, *_ = [guild for guild in self.bot.guilds if guild.name == "Brett"]
        general_channel, *_ = [channel for channel in brett_server.channels if channel.name == "général"]
        await general_channel.send("Bonjour, je suis en ligne.\r\nEnvoie '$help' pour savoir ce que je peux faire!")
        if self.export_members:
            save_json_file(get_member_dict(discord_client=self.bot), self.export_members, preserve=False)


    @commands.command(name='hello')
    async def _hello(self, ctx):
        """ Dis bonjour à l'utilisateur. """
        if ctx.author == self.last_hello_member:
            message = "Toi encore ?\r\nT'as rien de mieux à faire ?"
        else:
            self.last_hello_member = ctx.author
            message = f'Bonjour {ctx.author.display_name}!'

        await ctx.reply(message)

    @commands.command(name='test')
    @needs_administrator
    async def _test(self, ctx, *args):
        """ (Réservé aux admin) Commande de test qui renvoie les arguments. """
        await ctx.reply(" - ".join(args))

    @commands.command(name='bye')
    @needs_administrator
    async def _bye(self, ctx):
        """ (Réservé aux admin) Déconnecte le bot. """
        await ctx.reply("J'me déconnecte. Bye!")
        await self.bot.close()

    @commands.command(name='roles')
    @needs_manage_role
    async def _roles(self, ctx):
        """ (Réservé au bureau) Envoie un fichier JSON avec la liste des membres du serveur. """
        with tempfile.TemporaryDirectory() as temp_dir:
            json_filename = "members.json"
            member_info_json_file = Path(temp_dir) / json_filename
            save_json_file(get_member_dict(discord_client=self.bot,
                                        guild_names=([ctx.guild.name] if ctx.guild else None)),
                        member_info_json_file, preserve=False)
            await ctx.reply("Et voilà:",
                            file=discord.File(fp=member_info_json_file,
                                            filename=json_filename))

    # @commands.command(name='emargement')
    # @needs_administrator
    # async def _signsheet(self, ctx):
    #     """ (Réservé au bureau) Envoie la fiche d'émargement. """
    #     sign_sheet_filename="emargement.pdf"
    #     with self._gdrive.get_file(aj_config.file_id_presence) as sign_sheet:
    #         # with tempfile.TemporaryDirectory() as temp_dir:
    #         #     sign_sheet_file = Path(temp_dir) / sign_sheet_filename
    #         #     try:
    #         #         with open(sign_sheet_file, mode="wb") as fp:
    #         #             fp.write(sign_sheet)
    #         #         await ctx.reply("Et voilà:",
    #         #                         file=discord.File(fp=sign_sheet_file,
    #         #                                         filename=sign_sheet_filename))
    #         #     except Exception as e:
    #         #         print(e)
    #         #         raise
    #         await ctx.reply("Et voilà:",
    #                         file=discord.File(fp=sign_sheet,
    #                                         filename=sign_sheet_filename))

    @commands.command(name='seance')
    @needs_aj_manage_role
    async def _session(self, ctx, *, raw_input_date=None):
        """ (Réservé au bureau) Affiche le nombre de présent à une seance. Parametre = date. Si vide, prend la dernière séance enregistrée """
        session_dates = [s.date for s in self.ajdb.events.get_in_season_events(AjEvent.EVENT_TYPE_PRESENCE)]

        if not raw_input_date:
            input_date = max(session_dates)
        else:
            try:
                input_date = AjDate(dateparse(raw_input_date, settings=DATEPARSER_CONFIG))
            except TypeError:
                input_date = None

        if input_date:
            # look for closest date with presence
            session_date = min(session_dates, key=lambda x: abs(x - input_date))

            if session_date:
                reply = f"Il y a eu {len([s_date for s_date in session_dates if s_date == session_date])} participants à la séance du {session_date}."
            else:
                reply = f"Déso, pas trouvé de séance à la date du {raw_input_date} ou proche de cette date."
        else:
            reply = f"Mmmm... Ca m'étonnerait que '{raw_input_date}' soit une date."

        await ctx.reply(reply)

    @commands.command(name='membre')
    @needs_aj_manage_role
    async def _member(self, ctx, *, in_member):
        """ (Réservé au bureau) Affiche les infos des membres. Parametre = ID, pseudo discord ou nom (complet ou partiel)
            paramètre au choix:
                - ID (ex: 12, 124)
                - pseudo_discord (ex: VbrBot)
                - prénom nom ou nom prénom (sans guillement)
                  supporte des valeurs approximatives comme
                    - nom ou prenom seul
                    - nom et/ou prénom approximatif
                  retourne alors une liste avec la valeur de match)
        """
        members = await self.ajdb.members.search(in_member, ctx, 50, False)

        if members:
            reply = "\r\n".join([f"{member:short}" for member in members])
        else:
            reply = f"Je connais pas ton {in_member}."

        await ctx.reply(reply)



async def _async_bot(export_members = None):
    """ bot async function """

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    with AjConfig(break_if_missing=True, save_on_exit=True) as aj_config:
        try:
            bot = commands.Bot(command_prefix='$', intents=intents)
            await bot.add_cog(MyCommandsAndEvents(bot,
                                                  aj_config=aj_config,
                                                  export_members=export_members))
            token = credentials.get_set_discord(aj_config,
                                                prompt_if_present=False)
            await bot.start(token)

        except (discord.errors.LoginFailure, CredsException):
            await bot.close()
            print("Missing or Invalid token. Please define it using either set token using 'aj_setsecret'")

    print("Bot has shutdown.")


def _main():
    """ main function """
    asyncio.run(_async_bot(sys.argv[1] if len(sys.argv) > 1 else None))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
