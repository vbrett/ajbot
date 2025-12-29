""" List of function to handle app command outputs (Views, buttons, message, ...)
"""
from datetime import datetime, timedelta

import discord
from discord import Interaction, ui as dui

from ajbot._internal.config import FormatTypes, AjConfig
from ajbot._internal.ajdb import AjDb, tables as ajdb_t
from ajbot._internal import bot_in, bot_config
from ajbot._internal.exceptions import OtherException


# Generic Display functions
# ========================================================

def split_text(content:str,
               chunk_size=bot_config.CHUNK_MAX_SIZE,
               split_on_eol=True):
    """ Generator that splits content into chunks based on given limit.
        Can also ensure that split is only performed at eol.
        Yield each chunk.

        Supports content being None, in which case yields None.
    """
    if not content:
        yield None
        return

    assert (chunk_size <= bot_config.CHUNK_MAX_SIZE), f"La taille demandée {chunk_size} n'est pas supportée. Max {bot_config.CHUNK_MAX_SIZE}."

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
            first_answer = False
        else:
            chunk = bot_config.CHUNK_CONTINUE + chunk
        yield chunk


async def send_response_as_text(interaction: Interaction,
                                content:str,
                                embed=None,
                                ephemeral=False):
    """ Send basic command response, handling splitting it if needed based on discord limit.
        Can also ensure that split is only perform at eol.
    """

    for chunk in split_text(content):
        if interaction.response.type:
            message_fct = interaction.followup.send
        else:
            message_fct = interaction.response.send_message

        await message_fct(content=chunk, embed=embed, ephemeral=ephemeral)
        embed = None  # Empty embed so it is only send with the first chunk (even though, I doubt we will ever have embed with 2000+ content)


async def send_response_as_view(interaction: Interaction,
                                container:dui.Container=None,
                                title:str=None, summary:str=None, content:str=None,
                                ephemeral=False,):
    """ Send command response as a view, splitting content if needed.
    """
    assert container is not None or title is not None or summary is not None or content is not None, "Il faut fournir soit un container, soit des éléments à ajouter."
    assert not (container is not None and (title is not None or summary is not None or content is not None)), "Soit on fournit un container, soit des éléments à ajouter, mais pas les deux."

    for chunk in split_text(content):
        if not container:
            view = dui.LayoutView()
            container = dui.Container()
            view.add_item(container)

            if title:
                container.add_item(dui.TextDisplay(f'# __{title}__'))
            if summary:
                container.add_item(dui.TextDisplay(f'## {summary}'))
            if chunk:
                container.add_item(dui.TextDisplay(f'>>> {chunk}'))

        timestamp = discord.utils.format_dt(interaction.created_at, 'F')
        footer = dui.TextDisplay(f'-# Généré par {interaction.user} (ID: {interaction.user.id}) | {timestamp}')

        container.add_item(footer)

        if interaction.response.type:
            message_fct = interaction.followup.send
        else:
            message_fct = interaction.response.send_message

        await message_fct(view=container.view, ephemeral=ephemeral)
        container = None
        title = None        #display title & summary only on first chunk
        summary = None


# Detail display
# ========================================================


async def display_roles(aj_config:AjConfig,
                        aj_db:AjDb,
                        interaction: Interaction):
    """ Affiche les infos des roles
    """
    if not interaction.response.type:
        await interaction.response.defer(ephemeral=True,)

    discord_role_mismatches = {}
    aj_members = await aj_db.query_table_content(ajdb_t.Member)
    aj_discord_roles = await aj_db.query_table_content(ajdb_t.DiscordRole)
    default_asso_role_id = aj_config.asso_member_default
    default_discord_role_ids = [dr.id for dr in aj_discord_roles if default_asso_role_id in [ar.id for ar in dr.asso_roles]]

    for discord_member in interaction.guild.members:
        actual_role_ids = [r.id for r in discord_member.roles if r.name != "@everyone"]

        matched_members = [d for d in aj_members if d.discord_pseudo and d.discord_pseudo.name == discord_member.name]
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
                expected_role_ids = [dr.id for dr in member.current_asso_role.discord_roles]

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

    await send_response_as_view(interaction=interaction, title="Rôles", summary=summary, content=reply, ephemeral=True)


async def display_season(aj_db:AjDb,
                         interaction: Interaction,
                         season_name:str=None):
    """ Affiche les infos des évènements
    """
    if not interaction.response.type:
        await interaction.response.defer(ephemeral=True,)

    participants = await aj_db.query_members_per_season_presence(season_name)
    subscribers = await aj_db.query_members_per_season_presence(season_name, subscriber_only=True)
    format_style = FormatTypes.FULLSIMPLE if bot_in.is_manager(interaction) else FormatTypes.RESTRICTED

    if participants:
        summary = f"{len(participants)} personne(s) sont venues"

        reply = ''
        if len(subscribers) > 0:
            reply += f'## {len(subscribers)} Cotisant(es):\n- '
            reply += '\n- '.join(f'{m:{format_style}} - **{m.season_presence_count(season_name)}** participation(s)' for m in subscribers)
        if len(participants) - len(subscribers) > 0:
            reply += f'{"\n\n" if len(subscribers) else ''}## {len(participants) - len(subscribers)} non Cotisant(es):\n- '
            reply += '\n- '.join(f'{m:{format_style}} - **{m.season_presence_count(season_name)}** participation(s)' for m in participants if m not in subscribers)
    else:
        if subscribers:
            summary = f"Je ne sais pas combien de personne sont venues, mais {len(subscribers)} ont cotisé :"
            reply = '- ' + '\n- '.join(f'{m:{format_style}}' for m in subscribers)
        else:
            summary = "😱 Mais il n'y a eu personne ! 😱"
            reply = '---'

    await send_response_as_view(interaction=interaction,
                                title=f"Saison {season_name if season_name else 'en cours'}",
                                summary=summary,
                                content=reply,
                                ephemeral=True)


if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
