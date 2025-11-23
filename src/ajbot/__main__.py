""" This example requires the 'message_content' intent.
"""
import sys

from discord import Intents, errors

from ajbot._internal.bot import AjBot
from ajbot._internal.exceptions import CredsException
from ajbot._internal.config import AjConfig


def _main():
    """ main function """
    with AjConfig() as aj_config:
        token = aj_config.discord_token
        guild = aj_config.discord_guild

    intents = Intents.default()
    intents.message_content = True
    intents.members = True

    aj_bot = AjBot(guild=guild, intents=intents)

    try:
        aj_bot.client.run(token)
    except (errors.LoginFailure, CredsException):
        print("Token invalide ou manquant. Veuillez le définir en utilisant 'aj_creds'.")

    print("Le Bot a été arrêté.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
