''' Lookup tables
'''
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from ajbot._internal.exceptions import OtherException
from ajbot._internal.ajdb.support import Base


# class Asset(Base):
#TODO: ensure ERD is matching
#     """ Asset table class
#     """
#     __tablename__ = 'assets'
#
#     id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
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

#     id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, comment='UUID')
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


# class Log(Base):
#TODO: ensure ERD is matching
#     """ Log table class
#     """
#     __tablename__ = 'logs'
#     __table_args__ = (
#         sa.ForeignKeyConstraint(['author_id'], ['members.id'], name='FK_members_TO_log1'),
#         sa.ForeignKeyConstraint(['updated_event_id'], ['events.id'], name='FK_events_TO_log'),
#         sa.ForeignKeyConstraint(['updated_member_id'], ['members.id'], name='FK_members_TO_log'),
#         sa.ForeignKeyConstraint(['updated_membership_id'], ['memberships.id'], name='FK_memberships_TO_log'),
#         sa.ForeignKeyConstraint(['updated_transaction_id'], ['transactions.id'], name='FK_transaction_TO_log'),
#         sa.Index('FK_events_TO_log', 'updated_event_id'),
#         sa.Index('FK_members_TO_log', 'updated_member_id'),
#         sa.Index('FK_members_TO_log1', 'author_id'),
#         sa.Index('FK_memberships_TO_log', 'updated_membership_id'),
#         sa.Index('FK_transaction_TO_log', 'updated_transaction_id'),
#         sa.Index('UQ_datetime', 'log_datetime', unique=True)
#     )

#     log_datetime: orm.Mapped[datetime.datetime] = orm.mapped_column(sa.DateTime, primary_key=True)
#     author_id: orm.Mapped[AjMemberId] = orm.mapped_column(sa.Integer, nullable=False)
#  ?  name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
#     comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))
#     updated_event_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     updated_membership_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     updated_member_id: orm.Mapped[Optional[AjMemberId]] = orm.mapped_column(sa.Integer)
#     updated_transaction_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)

#     members: orm.Mapped['Member'] = orm.relationship(foreign_keys=[author], back_populates='logs', lazy='selectin')
#     events: orm.Mapped[Optional['Event']] = orm.relationship(back_populates='logs', lazy='selectin')
#     members_: orm.Mapped[Optional['Member']] = orm.relationship(foreign_keys=[updated_member], back_populates='log_', lazy='selectin')
#     memberships: orm.Mapped[Optional['Membership']] = orm.relationship(back_populates='logs', lazy='selectin')
#     transactions: orm.Mapped[Optional['Transaction']] = orm.relationship(back_populates='logs', lazy='selectin')


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
