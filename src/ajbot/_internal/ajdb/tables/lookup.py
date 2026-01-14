''' Lookup (constant) tables
'''
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from ajbot._internal.exceptions import OtherException
from .base import Base
if TYPE_CHECKING:
    from .membership import Membership
    from .member_private import PostalAddress


class StreetType(Base):
    """ Supported street type table class
    """
    __tablename__ = 'LUT_street_types'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    addresses: orm.Mapped[list['PostalAddress']] = orm.relationship(back_populates='street_type', foreign_keys='PostalAddress.street_type_id', lazy='selectin')

    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name


class ContributionType(Base):
    """ Supported contribution type table class
    """
    __tablename__ = 'LUT_contribution_types'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    memberships: orm.Mapped[list['Membership']] = orm.relationship(back_populates='contribution_type', foreign_keys='Membership.contribution_type_id', lazy='selectin')

    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name


class KnowFromSource(Base):
    """ Table class for source of knowing about the association
    """
    __tablename__ = 'LUT_know_from_sources'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    memberships: orm.Mapped[list['Membership']] = orm.relationship(back_populates='know_from_source', foreign_keys='Membership.know_from_source_id', lazy='selectin')

    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name


class AccountType(Base):
    """ Supported account type table class
    """
    __tablename__ = 'LUT_accounts'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    # transactions: orm.Mapped[list['Transaction']] = orm.relationship(back_populates='account_type', foreign_keys='Transaction.account_type_id', lazy='selectin')

    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
