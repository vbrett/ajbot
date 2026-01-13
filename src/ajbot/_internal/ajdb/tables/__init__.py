'''
AJ Database tables

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
then manually reformated
'''

from ajbot._internal.exceptions import OtherException
from .base import HumanizedDate, SaHumanizedDate, AjMemberId, SaAjMemberId
from .member import *
from .member_private import *
from .season import *
from .membership import *
from .lookup import *
from .role import *


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
