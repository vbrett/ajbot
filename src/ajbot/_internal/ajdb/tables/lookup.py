''' Lookup (constant) tables
'''
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from .base import BaseWithId
if TYPE_CHECKING:
    from .membership import Membership
    from .member_private import PostalAddress


class StreetType(BaseWithId):
    """ Supported street type table class
    """
    __tablename__ = 'LUT_street_types'

    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    addresses: orm.Mapped[list['PostalAddress']] = orm.relationship(back_populates='street_type', foreign_keys='PostalAddress.street_type_id', lazy='selectin')

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name


class ContributionType(BaseWithId):
    """ Supported contribution type table class
    """
    __tablename__ = 'LUT_contribution_types'

    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    memberships: orm.Mapped[list['Membership']] = orm.relationship(back_populates='contribution_type', foreign_keys='Membership.contribution_type_id', lazy='selectin')

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name


class KnowFromSource(BaseWithId):
    """ Table class for source of knowing about the association
    """
    __tablename__ = 'LUT_know_from_sources'

    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    memberships: orm.Mapped[list['Membership']] = orm.relationship(back_populates='know_from_source', foreign_keys='Membership.know_from_source_id', lazy='selectin')

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name


class AccountType(BaseWithId):
    """ Supported account type table class
    """
    __tablename__ = 'LUT_accounts'

    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    # transactions: orm.Mapped[list['Transaction']] = orm.relationship(back_populates='account_type', foreign_keys='Transaction.account_type_id', lazy='selectin')

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name
