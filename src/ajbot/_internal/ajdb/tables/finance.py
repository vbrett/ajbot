''' Finance related db tables
'''
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from ajbot._internal.exceptions import OtherException
from .base import BaseWithId


# class Asset(Base):
#TODO: ensure ERD is matching
#     """ Asset table class
#     """
#     __tablename__ = 'assets'
#
#     name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)
#     description: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))
#
#     transactions: orm.Mapped[list['Transaction']] = orm.relationship(back_populates='assets', lazy='selectin')


# class Transaction(Base):
#TODO: ensure ERD is matching
#     """ Transaction table class
#     """
#     __tablename__ = 'transactions'
#     __table_args__ = (
#         sa.ForeignKeyConstraint(['account'], ['LUT_accounts.id'], name='FK_LUT_accounts_TO_transaction'),
#         sa.ForeignKeyConstraint(['associated_asset'], ['assets.id'], name='FK_assets_TO_transaction'),
#         sa.ForeignKeyConstraint(['associated_event'], ['events.id'], name='FK_events_TO_transaction'),
#         sa.ForeignKeyConstraint(['associated_membership'], ['memberships.id'], name='FK_memberships_TO_transaction'),
#         sa.Index('FK_LUT_accounts_TO_transaction', 'account'),
#         sa.Index('FK_assets_TO_transaction', 'associated_asset'),
#         sa.Index('FK_events_TO_transaction', 'associated_event'),
#         sa.Index('FK_memberships_TO_transaction', 'associated_membership'),
#         sa.Index('UQ_transaction_id', 'transaction_id', unique=True)
#     )

#     date: orm.Mapped[HumanizedDate] = orm.mapped_column(saHumanized.Date, nullable=False)
#     season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.id'), nullable=False, comment='shall be computed based on transaction_date', index=True)
#     account: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
#     associated_event: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     associated_asset: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     associated_membership: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     title: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50), comment='non empty only if all associated_xxx are empty')
#     details: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(100))
#     credit: orm.Mapped[Optional[float]] = orm.mapped_column(sa.Float)
#     debit: orm.Mapped[Optional[float]] = orm.mapped_column(sa.Float)
#     comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))

#     account_type: orm.Mapped['AccountType'] = orm.relationship(back_populates='transactions', lazy='selectin')
#     assets: orm.Mapped[Optional['Asset']] = orm.relationship(back_populates='transactions', lazy='selectin')
#     events: orm.Mapped[Optional['Event']] = orm.relationship(back_populates='transactions', lazy='selectin')
#     memberships: orm.Mapped[Optional['Membership']] = orm.relationship(back_populates='transactions', lazy='selectin')
#     seasons: orm.Mapped['Season'] = orm.relationship(back_populates='transactions', lazy='selectin')
#     logs: orm.Mapped[list['Log']] = orm.relationship(back_populates='transactions', lazy='selectin')


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
