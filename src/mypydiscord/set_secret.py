''' Handle storing secrets in system keyring
'''

import sys
import keyring
from pwinput import pwinput

from ._internal.config import DISCORD_KEY_SERVER, DISCORD_KEY_USER, DISCORD_KEY_AJDB

def _main():
    """ Simple command line interface to set the passwords in the keyring. """

    action = '' if not keyring.get_password(DISCORD_KEY_SERVER, DISCORD_KEY_USER) else input("Le token d'accès à Discord est déjà défini. Voulez-vous le remplacer ? (o/n) ")
    if action.lower() == 'o':
        password = pwinput("Entrez le token d'accès à Discord : ")
        keyring.set_password(DISCORD_KEY_SERVER, DISCORD_KEY_USER, password)

    action = '' if not keyring.get_password(DISCORD_KEY_SERVER, DISCORD_KEY_AJDB) else input("Le token d'accès à la base de données AJ est déjà défini. Voulez-vous le remplacer ? (o/n) ")
    if action.lower() == 'o':
        password = pwinput("Entrez le token d'accès à la base de données AJ : ")
        keyring.set_password(DISCORD_KEY_SERVER, DISCORD_KEY_AJDB, password)
    return 0


if __name__ == '__main__':
    sys.exit(_main())
