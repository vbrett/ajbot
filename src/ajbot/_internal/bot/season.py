""" Function roles outputs (Views, buttons, message, ...)
"""
from discord import Interaction

from ajbot._internal.config import FormatTypes
from ajbot._internal.ajdb import AjDb
from ajbot._internal.bot import checks, responses


async def display(aj_db:AjDb,
                         interaction: Interaction,
                         season_name:str=None):
    """ Affiche les infos des évènements
    """
    if not interaction.response.type:
        await interaction.response.defer(ephemeral=True,)

    participants = await aj_db.query_members_per_season_presence(season_name)
    subscribers = await aj_db.query_members_per_season_presence(season_name, subscriber_only=True)
    format_style = FormatTypes.FULLSIMPLE if checks.is_manager(interaction) else FormatTypes.RESTRICTED

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

    await responses.send_response_as_view(interaction=interaction,
                                          title=f"Saison {season_name if season_name else 'en cours'}",
                                          summary=summary,
                                          content=reply,
                                          ephemeral=True)
