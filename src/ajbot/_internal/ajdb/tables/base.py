'''
Base functions and classes for aj Database.
'''
from typing import Optional, TYPE_CHECKING
from abc import ABC

import datetime

import sqlalchemy as sa
from sqlalchemy.ext import asyncio as aio_sa
from sqlalchemy import orm
# from sqlalchemy.ext.declarative import declared_attr

from ajbot._internal.types import AjDate, AjMemberId, AjId
from ajbot._internal.exceptions import OtherException
if TYPE_CHECKING:
    from .member import Member

class SaAjDate(ABC, sa.types.TypeDecorator):
    """ SqlAlchemy class to report date using AjDate custom class
    """
    impl = sa.Date
    cache_ok = True
    _default_type = sa.Date

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, AjDate):
            value = AjDate(value)
        return datetime.date(value.year, value.month, value.day)

    def process_result_value(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, AjDate):
            value = AjDate(value)
        return value


class SaAjMemberId(ABC, sa.types.TypeDecorator):
    """ SqlAlchemy class to report member id using AjMemberId custom class
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

class SaAjId(ABC, sa.types.TypeDecorator):
    """ SqlAlchemy class to report generic db id using AjId custom class
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
