"""
Group module custom types
"""
import datetime

from ajbot._internal.exceptions import OtherException, AjTypeException
from ajbot._internal.config import AJ_ID_PREFIX

class AjDate(datetime.date):
    """ class that handles date type for AJ DB
    """
    def __new__(cls, indate, *args, **kwargs):
        #check if first passed argument is already a datetime format
        if not isinstance(indate, datetime.date):
            raise AjTypeException(f"Incorrect format: {type(cls)}")

        return super().__new__(cls, indate.year, indate.month, indate.day, *args, **kwargs)

    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return self.strftime('%d/%m/%Y')


class AjMemberId(int):
    """ Class that handles member id as integer, and represents it in with correct format
    """
    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return f"{AJ_ID_PREFIX}{str(int(self)).zfill(5)}"


class AjId(int):
    """ Class that handles generic db id as integer, and represents it in with correct format
    """
    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return f"#{str(int(self))}"


class DiscordId(int):
    """ Class that handles discord id as integer, and represents it in with correct format
    """
    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return f"{str(int(self))}"


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
