''' contains configuration variables
'''

from ajbot._internal.exceptions import OtherException

KEY_SERVER = "ajbot"
KEY_USER_DISCORD = "discord"
KEY_USER_DRIVE = "db"

AJ_DISCORD_ID = 691003175037042788
AJ_DB_FILE_ID = "1OATzmXMK-ssWjGjGY9rI6TOX99DLboEf"
AJ_TABLE_NAME_SUIVI = "suivi"
AJ_TABLE_NAME_ANNUAIRE = "annuaire"

# If modifying these scopes, delete the file token.json.
AJ_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
