''' Handle storing secrets in config file.
'''

import sys

from pwinput import pwinput

from ajbot._internal.config import AjConfig
from ajbot._internal.exceptions import CredsException


def check_set_discord(aj_config:AjConfig):
    """ Get the Discord token from the conf file. If not found, ask for it and store it.

    Args:
        aj_config: AjConfig object to use to store the token.
    Returns:
        The Discord token, None if not found and not set.
    """
    token = aj_config.discord_token

    if token:
        action = input("Le token d'accès à Discord est déjà défini. Voulez-vous le remplacer ? (o/n) ")
        if action.lower() != 'o':
            return token

    elif aj_config.break_if_missing:
        raise CredsException("Le token d'accès à Discord n'est pas défini.")

    token = pwinput("Entrez le token d'accès à Discord : ")
    if token:
        aj_config.discord_token = token
        return token

    if aj_config.break_if_missing:
        raise CredsException("Le token d'accès à Discord n'est pas défini.")

    return None


def check_set_db(aj_config:AjConfig):
    """ Get the db credentials from the conf file. If not found, ask for it and store it.
    Args:
        aj_config: AjConfig object to use to store the credentials information
    Returns:
        The db credential object, None if not found and not set.
    """
    token = aj_config.db_creds
    #TODO: do more detailed checks on validity of the credentials

    if token:
        action = input("Les informations d'accès à la base de données sont déjà définies. Voulez-vous le remplacer ? (o/n) ")
        if action.lower() != 'o':
            return token

    #TODO: Add credential update

    if aj_config.break_if_missing:
        raise CredsException("Le token d'accès à la base de données n'est pas défini ou n'est pas valide.")

    return None


def _main():
    """ Simple command line interface to set or update the passwords & credentials in config file. """
    with AjConfig(break_if_missing=False, save_on_exit=True) as aj_config:
        _ = check_set_discord(aj_config)
        _ = check_set_db(aj_config)
    return 0


if __name__ == '__main__':
    sys.exit(_main())
