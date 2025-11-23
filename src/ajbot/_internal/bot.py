""" Discord bot
"""
from typing import Optional
# import tempfile
# from pathlib import Path

import discord
from discord import app_commands, Interaction, ui as dui
# from dateparser import parse as dateparse
# from vbrpytools.dicjsontools import save_json_file

from ajbot import __version__ as ajbot_version
from ajbot._internal import bot_elements as bot
from ajbot._internal.ajdb import AjDb
from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal.exceptions import AjBotException, OtherException
from ajbot._internal.config import FormatTypes #, DATEPARSER_CONFIG

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
        @app_commands.check(bot.is_manager)
        @app_commands.checks.cooldown(1, 5)
        async def version(interaction: Interaction):
            """ Affiche la version du bot
            """
            await self.send_response_as_text(interaction=interaction,
                                             content=f"Version du bot: {ajbot_version}",
                                             ephemeral=True)

        @self.client.tree.command(name="bonjour")
        @app_commands.check(bot.is_member)
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
            await self.send_response_as_text(interaction=interaction,
                                           content=message_list[self.last_hello_member_count],
                                           ephemeral=True)


        # Member related commands
        # ========================================================
        @self.client.tree.command(name="cqui")
        @app_commands.check(bot.is_member)
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
            await self.send_member_info(interaction=interaction,
                                        disc_member=disc_member,
                                        int_member=int_member,
                                        str_member=str_member)


        # Season related commands
        # ========================================================

        @self.client.tree.command(name="cotisants")
        @app_commands.check(bot.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @bot.with_season_name
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

                format_style = FormatTypes.FULLSIMPLE if bot.is_manager(interaction) else FormatTypes.RESTRICTED
                reply = '- ' + '\n- '.join(f'{m:{format_style}}' for m in members)
            else:
                summary = "Mais il n'y a eu personne cette saison ;-("
                reply = '---'

            # await self.send_response_basic(interaction, content=reply, ephemeral=True, split_on_eol=True)
            await self.send_response_as_view(interaction=interaction, title="Cotisants", summary=summary, content=reply, ephemeral=True)

        @self.client.tree.command(name="evenements")
        @app_commands.check(bot.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @bot.with_season_name
        async def events(interaction: Interaction,
                         season_name:Optional[str]=None,
                         ):
            """ Affiche la liste des evenements d'une saison donnée
            """
            async with AjDb() as aj_db:
                events = await aj_db.query_events(season_name)

            if events:
                if season_name:
                    summary = f"Il y a eu {len(events)} évènement(s) lors de la saison {season_name} :"
                else:
                    summary = f"Il y a déjà eu {len(events)} évènement(s) lors de cette saison :"

                format_style = FormatTypes.FULLSIMPLE if bot.is_manager(interaction) else FormatTypes.RESTRICTED
                reply = '- ' + '\n- '.join(f'{e:{format_style}}' for e in events)
            else:
                summary = "Mais il n'y a eu aucun évènement cette saison ;-("
                reply = '---'

            # await self.send_response_basic(interaction, content=reply, ephemeral=True, split_on_eol=True)
            await self.send_response_as_view(interaction=interaction, title="Evènements", summary=summary, content=reply, ephemeral=True)

        @self.client.tree.command(name="presence")
        @app_commands.check(bot.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @bot.with_season_name
        async def presence(interaction: Interaction,
                           season_name:Optional[str]=None,
                           ):
            """ Affiche les personne ayant participé à une saison donnée
            """
            async with AjDb() as aj_db:
                members = await aj_db.query_members_per_season_presence(season_name)

            if members:
                members.sort(key=lambda x: x, reverse=False)
                if season_name:
                    summary = f"{len(members)} personne(s) sont venus lors de la saison {season_name} :"
                else:
                    summary = f"{len(members)} personne(s) sont déjà venus lors de cette saison :"

                format_style = FormatTypes.FULLSIMPLE if bot.is_manager(interaction) else FormatTypes.RESTRICTED
                reply = '- ' + '\n- '.join(f'{m:{format_style}} - {m.season_presence_count(season_name)} participation(s)' for m in members)
            else:
                summary = "Mais il n'y a eu personne cette saison ;-("
                reply = "---"

            # await self.send_response_basic(interaction, content=content, ephemeral=True, split_on_eol=True)
            await self.send_response_as_view(interaction=interaction, title="Présence", summary=summary, content=reply, ephemeral=True)

        @self.client.tree.command(name="gérer_évènement")
        @app_commands.check(bot.is_manager)
        @app_commands.checks.cooldown(1, 5)
        @app_commands.rename(event='évènement')
        @app_commands.describe(event='évènement à modifier (aucun = crée un nouvel évènement)')
        @app_commands.autocomplete(event=bot.AutocompleteFactory(ajdb_t.Event).ac)
        async def event_handler(interaction: Interaction,
                                event:Optional[str]=None,
                                ):
            """ Créer un nouvel évènement ou modifie un existant
            """
            eventmodal = await bot.CreateEventModal.create(event)
            await interaction.response.send_modal(eventmodal)


        # ========================================================
        # List of context menu commands for the bot
        # ========================================================

        @self.client.tree.context_menu(name='Info membre')
        @app_commands.check(bot.is_member)
        async def show_name(interaction: Interaction, member: discord.Member):
            await self.send_member_info(interaction=interaction, disc_member=member)


        # ========================================================
        # Error handling
        # =================================================

        @self.client.tree.error
        async def error_report(interaction: Interaction, exception):
            if isinstance(exception, app_commands.CommandOnCooldown):
                error_message = "😵‍💫 Ouh là, tout doux le foufou, tu vas trop vite pour moi .\r\n\r\nRenvoie ta commande un peu plus tard."
            else:
                error_message =f"😱 Oups ! un truc chelou c'est passé.\r\n{exception}"

            await self.send_response_as_text(interaction=interaction, content=error_message, ephemeral=True)


    # ========================================================
    # Support functions
    # ========================================================
    async def send_response_as_text(self, interaction: Interaction,
                                    content:str, ephemeral=False, delete_after=None,
                                    chunk_size=1800, split_on_eol=True):
        """ Send basic command response, handling splitting it if needed (limit = 2000 characters).
            Can also ensure that split is only perform at eol.
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
                await interaction.response.send_message(chunk, ephemeral=ephemeral, delete_after=delete_after)
                first_answer = False
            else:
                await interaction.followup.send('(...)\n' + chunk, ephemeral=ephemeral, delete_after=delete_after)

    async def send_response_as_view(self, interaction: Interaction,
                                 title:str, summary:str, content:str,
                                 ephemeral=False,):
        """ Send command response as a view
        """
        view = dui.LayoutView()
        container = dui.Container()
        view.add_item(container)

        container.add_item(dui.TextDisplay(f'# __{title}__'))
        container.add_item(dui.TextDisplay(f'## {summary}'))
        container.add_item(dui.TextDisplay(f'>>> {content}'))

        timestamp = discord.utils.format_dt(interaction.created_at, 'F')
        footer = dui.TextDisplay(f'-# Généré par {interaction.user} (ID: {interaction.user.id}) | {timestamp}')

        container.add_item(footer)
        await interaction.response.send_message(view=view, ephemeral=ephemeral)


    async def send_member_info(self, interaction: Interaction,
                               disc_member:discord.Member=None,
                               int_member:int=None,
                               str_member:str=None,
                               delete_after=None):
        """ Affiche les infos des membres
        """
        input_member = [x for x in [disc_member, str_member, int_member] if x is not None]
        if len(input_member) != 1:
            input_types="un (et un seul) élément parmi:\r\n* un pseudo\r\n* un nom\r\n* un ID"
            if len(input_member) == 0:
                message = f"😓 Alors là, je vais avoir du mal à trouver sans un minimum d'info, à savoir {input_types}"
            else:
                message = f"🤢 Tu dois fournir {input_types}\r\nMais pas de mélange, c'est pas bon pour ma santé"
            await self.send_response_as_text(interaction=interaction,
                                             content=message,
                                             ephemeral=True)
            return
        [input_member] = input_member

        async with AjDb() as aj_db:
            members = await aj_db.query_members_per_id_info(input_member, 50, False)

        embed = None
        view = None
        reply = None
        if members:
            if len(members) == 1:
                class EditButton(dui.Button):
                    """ Class that creates a edit button
                    """
                    def __init__(self):
                        super().__init__(style=discord.ButtonStyle.primary, label='Editer', row=2)

                    async def callback(self, interaction: discord.Interaction):
                        await interaction.response.send_message(content="Pas encore disponible", ephemeral=True, delete_after=10)

                [member] = members
                is_self = member.discord_pseudo.name == interaction.user.name
                format_style = FormatTypes.FULLSIMPLE if (is_self or bot.is_manager(interaction)) else FormatTypes.RESTRICTED
                view = dui.LayoutView()
                container = dui.Container()
                view.add_item(container)

                container.add_item(dui.Section(dui.TextDisplay(format(member, format_style)),
                                               accessory=EditButton()))
            else:
                #TODO: transform embed to view - once view can support tables
                embed = discord.Embed(color=discord.Color.orange())
                format_style = FormatTypes.FULLSIMPLE if (bot.is_manager(interaction)) else FormatTypes.RESTRICTED
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
        else:
            reply = f"Je ne connais pas ton ou ta {input_member}."

        await interaction.response.send_message(content=reply, embed=embed, view=view, ephemeral=True, delete_after=delete_after)


#     @commands.command(name='roles')
#     @needs_manage_role
#     async def _roles(self, ctx):
#         """ (Réservé au bureau) Envoie un fichier JSON avec la liste des membres du serveur. """
#         with tempfile.TemporaryDirectory() as temp_dir:
#             json_filename = "members.json"
#             member_info_json_file = Path(temp_dir) / json_filename
#             save_json_file(bot.get_discord_members(discord_client=self.bot,
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
