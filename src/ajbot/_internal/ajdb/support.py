'''
Support functions and classes for aj Database.
'''

import datetime
import humanize

import sqlalchemy as sa
from sqlalchemy.ext import asyncio as aio_sa
from sqlalchemy import orm

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import AJ_ID_PREFIX


class HumanizedDate(datetime.date):
    """ class that handles date type for AJ DB
    """
    def __new__(cls, indate, *args, **kwargs):
        #check if first passed argument is already a datetime format
        if not isinstance(indate, datetime.date):
            raise AjDbException(f"Incorrect format: {type(cls)}")

        return super().__new__(cls, indate.year, indate.month, indate.day, *args, **kwargs)

    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        humanize.activate("fr_FR")
        humanized_date = humanize.naturaldate(self)
        humanize.deactivate()
        return humanized_date

class SaHumanizedDate(sa.types.TypeDecorator):          #pylint: disable=abstract-method
    """ SqlAlchemy class to report date using specific class
    """
    impl = sa.Date
    cache_ok = True
    _default_type = sa.Date

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, HumanizedDate):
            value = HumanizedDate(value)
        return datetime.date(value.year, value.month, value.day)

    def process_result_value(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, HumanizedDate):
            value = HumanizedDate(value)
        return value


class AjMemberId(int):
    """ Class that handles member id as integer, and represents it in with correct format
    """
    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return f"{AJ_ID_PREFIX}{str(int(self)).zfill(5)}"

class SaAjMemberId(sa.types.TypeDecorator):   #pylint: disable=abstract-method
    """ SqlAlchemy class to report member id using specific class
    """
    impl = sa.Integer
    cache_ok = True
    _default_type = sa.Integer

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, AjMemberId):
            value = AjMemberId(value)
        return int(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, AjMemberId):
            value = AjMemberId(value)
        return value


class Base(aio_sa.AsyncAttrs, orm.DeclarativeBase):
    """ Base ORM class
    """


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
