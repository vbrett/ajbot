''' contains configuration variables
'''

from ajbot._internal.exceptions import OtherException

KEY_SERVER = "ajbot"
KEY_USER_DISCORD = "discord"
KEY_USER_DRIVE = "db"

DATEPARSER_CONFIG = {'DATE_ORDER': 'DMY', 'DEFAULT_LANGUAGES': ["fr"]}

DISCORD_ID_AJ = 691003175037042788
DISCORD_ID_DEBUG = 1418999792498901167

AJ_PRESENCE_FILE_ID = "1-hDwJETkllIwNLNHKGl3iCW-pzwWqKbY"
AJ_DB_FILE_ID = "1OATzmXMK-ssWjGjGY9rI6TOX99DLboEf"
AJ_TABLE_NAME_EVENTS = "suivi"
AJ_TABLE_NAME_ROSTER = "annuaire"
AJ_TABLE_NAME_ROLE = "roles"
AJ_TABLE_EVENT_TYPE = "categories"

# Google credential needed scope (If modifying these scopes, delete the file token.json.)
AJ_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
