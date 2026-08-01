""" Discord bot
"""
from ajbot._internal.exceptions import OtherException

from .api import *

if __name__ == "__main__":
    raise OtherException('This module is not meant to be executed directly.')
