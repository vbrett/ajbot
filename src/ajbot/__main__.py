""" This example requires the 'message_content' intent.
"""
import sys

from discord import Intents, errors

from ajbot import credentials
from ajbot._internal.bot import AjBot
from ajbot._internal.exceptions import CredsException
from ajbot._internal.config import AjConfig


def _main():
    """ main function """
    with AjConfig(break_if_missing=True,
                  save_on_exit=True) as aj_config:


        intents = Intents.default()
        intents.message_content = True
        intents.members = True

        aj_bot = AjBot(aj_config, intents)

        token = credentials.get_set_discord(aj_config,
                                            prompt_if_present=False)

        # ensure any changes are saved before running
        aj_config.save()  #TODO: change class to non context mgr?
        try:
            aj_bot.client.run(token)
        except (errors.LoginFailure, CredsException):
            print("Missing or Invalid token. Please define it using either set token using 'aj_setsecret'")

    print("Bot has shutdown.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
