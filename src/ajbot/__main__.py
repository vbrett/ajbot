""" This example requires the 'message_content' intent.
"""
import sys
import asyncio
from functools import wraps
import tempfile
from pathlib import Path

import discord
from discord.ext import commands

from vbrpytools.dicjsontools import save_json_file

from ajbot._internal.exceptions import SecretException
from ajbot import credentials


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

class MyCommandsAndEvents(commands.Cog):
    """ A class to hold bot commands. """
    def __init__(self, bot, export_members = None):
        self.bot = bot
        self.last_hello_member = None
        self.export_members = export_members

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
        """ Commande de test qui renvoie les arguments. """
        await ctx.reply(" - ".join(args))

    @commands.command(name='bye')
    @needs_administrator
    async def _bye(self, ctx):
        """ Déconnecte le bot. """
        await ctx.reply("J'me déconnecte. Bye!")
        await self.bot.close()

    @commands.command(name='members')
    @needs_manage_role
    async def _members(self, ctx):
        """ Envoie un fichier JSON avec la liste des membres du serveur. """
        with tempfile.TemporaryDirectory() as temp_dir:
            json_filename = "members.json"
            member_info_json_file = Path(temp_dir) / json_filename
            save_json_file(get_member_dict(discord_client=self.bot,
                                           guild_names=([ctx.guild.name] if ctx.guild else None)),
                           member_info_json_file, preserve=False)
            await ctx.reply("Et voilà:",
                            file=discord.File(fp=member_info_json_file,
                                              filename=json_filename))

async def _async_bot(export_members = None):
    """ bot async function """
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    try:
        bot = commands.Bot(command_prefix='$', intents=intents)
        await bot.add_cog(MyCommandsAndEvents(bot, export_members=export_members))
        token = credentials.get_set_discord(prompt_if_present=False,
                                            break_if_missing=True)
        await bot.start(token)

    except (discord.errors.LoginFailure, SecretException):
        await bot.close()
        print("Missing or Invalid token. Please define it using either set token using 'aj_setsecret'")

    print("Bot has shutdown.")


def _main():
    """ main function """
    asyncio.run(_async_bot(sys.argv[1] if len(sys.argv) > 1 else None))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
