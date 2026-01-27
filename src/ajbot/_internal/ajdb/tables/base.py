'''
Base functions and classes for aj Database.
'''
from typing import Optional, TYPE_CHECKING
from abc import ABC

import datetime
import humanize

import sqlalchemy as sa
from sqlalchemy.ext import asyncio as aio_sa
from sqlalchemy import orm
# from sqlalchemy.ext.declarative import declared_attr

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import AJ_ID_PREFIX
if TYPE_CHECKING:
    from .member import Member


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

class SaHumanizedDate(ABC, sa.types.TypeDecorator):
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

class SaAjMemberId(ABC, sa.types.TypeDecorator):
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


class AjId(int):
    """ Class that handles generic db id as integer, and represents it in with correct format
    """
    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return f"#{str(int(self))}"

class SaAjId(ABC, sa.types.TypeDecorator):
    """ SqlAlchemy class to report generic db id using specific class
    """
    impl = sa.Integer
    cache_ok = True
    _default_type = sa.Integer

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, AjId):
            value = AjId(value)
        return int(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, AjId):
            value = AjId(value)
        return value


class BaseWithId(aio_sa.AsyncAttrs, orm.DeclarativeBase):
    """ Base ORM class
    """

    id: orm.Mapped[AjId] = orm.mapped_column(SaAjId, primary_key=True, index=True, unique=True, autoincrement=True)

class LogMixin:
    """ Abstract mixin for tables with log information : update timestamp & author
    """
    log_timestamp: orm.Mapped[Optional[datetime.datetime]] = orm.mapped_column(sa.DateTime(timezone=True),
                                                                               server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
                                                                               nullable=True, index=True)

    @orm.declared_attr
    def log_author_id(cls) -> orm.Mapped[Optional[AjMemberId]]: #pylint: disable=no-self-argument    #cannot use @classmethod, don't know why
        """
        Attribute declarator class method to register log_author_id attribute
        """
        return orm.mapped_column(SaAjMemberId, sa.ForeignKey('members.id', name=f'fk_{cls.__name__}_log_author_id'), index=True, nullable=True)

    @orm.declared_attr
    def log_author(cls) -> orm.Mapped[Optional['Member']]:      #pylint: disable=no-self-argument    #cannot use @classmethod, don't know why
        """
        Attribute declarator class method to register log_author relationship
        """
        return orm.relationship(foreign_keys=f"{cls.__name__}.log_author_id", lazy='selectin')


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
