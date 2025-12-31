""" List of function to handle app command outputs (Views, buttons, message, ...)
"""

import discord
from discord import Interaction, ui as dui

from ajbot._internal.bot import  params
from ajbot._internal.exceptions import OtherException


def split_text(content:str,
               chunk_size=params.CHUNK_MAX_SIZE,
               split_on_eol=True):
    """ Generator that splits content into chunks based on given limit.
        Can also ensure that split is only performed at eol.
        Yield each chunk.

        Supports content being None, in which case yields None.
    """
    if not content:
        yield None
        return

    assert (chunk_size <= params.CHUNK_MAX_SIZE), f"La taille demandée {chunk_size} n'est pas supportée. Max {params.CHUNK_MAX_SIZE}."

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
            chunk = params.CHUNK_CONTINUE + chunk
        yield chunk


async def send_response_as_text(interaction: Interaction,
                                content:str,
                                embed=None,
                                ephemeral=False,
                                file=None):
    """ Send basic command response, handling splitting it if needed based on discord limit.
        Can also ensure that split is only perform at eol.
    """

    for chunk in split_text(content):
        if interaction.response.type:
            message_fct = interaction.followup.send
        else:
            message_fct = interaction.response.send_message

        if file:
            await message_fct(content=chunk, embed=embed, ephemeral=ephemeral, file=file)
            file = None  # Empty file so it is only send with the first chunk (even though, I doubt we will ever have file with 2000+ content)
        else:
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


if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
