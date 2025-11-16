''' manage AJ database

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
then manually reformated
'''
from typing import Optional
import datetime
import functools

import sqlalchemy as sa
from sqlalchemy.ext import asyncio as aio_sa
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import orm

from thefuzz import fuzz
import humanize
import discord
from discord.ext.commands import MemberNotFound

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import AjConfig, _AJ_ID_PREFIX, FormatTypes


class HumanizedDate(datetime.date):
    """ class that handles date type for AJ DB
    """
    def __new__(cls, indate, *args, **kwargs):
        #check if first passed argument is already a datetime format
        if not isinstance(indate, datetime.date):
            raise AjDbException(f'Incorrect format: {type(cls)}')

        return super().__new__(cls, indate.year, indate.month, indate.day, *args, **kwargs)

    def __str__(self):
        return f'{self}'

    def __format__(self, _format_spec):
        """ override format
        """
        humanize.activate("fr_FR")
        humanized_date = humanize.naturaldate(self)
        humanize.deactivate()
        return humanized_date

class SaHumanizedDate(sa.types.TypeDecorator):          #pylint: disable=abstract-method,abstract-method
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
        return f'{self}'

    def __format__(self, _format_spec):
        """ override format
        """
        return f"{_AJ_ID_PREFIX}{str(int(self)).zfill(5)}"

class SaAjMemberId(sa.types.TypeDecorator):   #pylint: disable=abstract-method,abstract-method
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


# Lookup tables
################################


class StreetType(Base):
    """ Supported street type table class
    """
    __tablename__ = 'LUT_street_types'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    addresses: orm.Mapped[list['PostalAddress']] = orm.relationship('PostalAddress', back_populates='street_type', lazy='selectin')

    def __str__(self):
        return f'{self}'

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

    memberships: orm.Mapped[list['Membership']] = orm.relationship('Membership', back_populates='contribution_type', lazy='selectin')

    def __str__(self):
        return f'{self}'

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

    memberships: orm.Mapped[list['Membership']] = orm.relationship('Membership', back_populates='know_from_source', lazy='selectin')

    def __str__(self):
        return f'{self}'

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

    # transactions: orm.Mapped[list['Transaction']] = orm.relationship('Transaction', back_populates='account_type', lazy='selectin')

    def __str__(self):
        return f'{self}'

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name


# Main tables
################################


class Season(Base):
    """ Season table class
    """
    __tablename__ = 'seasons'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(10), nullable=False, index=True)
    start: orm.Mapped[HumanizedDate] = orm.mapped_column(SaHumanizedDate, nullable=False, unique=True)
    end: orm.Mapped[HumanizedDate] = orm.mapped_column(SaHumanizedDate, nullable=False)

    memberships: orm.Mapped[list['Membership']] = orm.relationship('Membership', back_populates='season', lazy='selectin')
    events: orm.Mapped[list['Event']] = orm.relationship('Event', back_populates='season', lazy='selectin')
    # transactions: orm.Mapped[list['Transaction']] = orm.relationship('Transaction', back_populates='seasons')

    @hybrid_property
    def is_current_season(self):
        """ return true if item is current season
        """
        return (    datetime.datetime.now().date() >= self.start
                and datetime.datetime.now().date() <= self.end)

    @is_current_season.expression
    def is_current_season(cls):      #pylint: disable=no-self-argument   #function is a class factory
        """ SQL version
        """
        return  sa.select(
                    sa.case((sa.exists().where(
                    sa.and_(
                        datetime.datetime.now().date() >= cls.start,
                        datetime.datetime.now().date() <= cls.end)).correlate(cls), True), else_=False,
                    ).label("is_current_season")
                ).scalar_subquery()

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return ((self.start, self.end) ==
                (other.start, other.end))

    def __lt__(self, other):
        return ((self.start, self.end) <
                (other.start, other.end))

    def __str__(self):
        return f'{self}'

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name


@functools.total_ordering
class Member(Base):
    """ Member table class
    """
    __tablename__ = 'members'

    id: orm.Mapped[AjMemberId] = orm.mapped_column(SaAjMemberId, primary_key=True, index=True, unique=True, autoincrement=True)

    credential_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('member_credentials.id'), index=True, nullable=True)
    credential: orm.Mapped[Optional['Credential']] = orm.relationship('Credential', back_populates='member', uselist=False, lazy='selectin')
    discord_pseudo_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('discord_pseudos.id'), index=True, nullable=True)
    discord_pseudo: orm.Mapped[Optional['DiscordPseudo']] = orm.relationship('DiscordPseudo', back_populates='member', uselist=False, lazy='selectin')
    asso_roles: orm.Mapped[list['MemberAssoRole']] = orm.relationship('MemberAssoRole', back_populates='member', lazy='selectin')
    emails: orm.Mapped[list['MemberEmail']] = orm.relationship('MemberEmail', back_populates='member', lazy='selectin')
    email_principal: orm.Mapped[Optional['MemberEmail']] = orm.relationship('MemberEmail',
                                                                                primaryjoin="and_(Member.id==MemberEmail.member_id,MemberEmail.principal==True)",
                                                                                lazy='selectin',
                                                                                viewonly=True,)
    phones: orm.Mapped[list['MemberPhone']] = orm.relationship('MemberPhone', back_populates='member', lazy='selectin')
    phone_principal: orm.Mapped[Optional['MemberPhone']] = orm.relationship('MemberPhone',
                                                                             primaryjoin="and_(Member.id==MemberPhone.member_id,MemberPhone.principal==True)",
                                                                             lazy='selectin',
                                                                             viewonly=True,)
    addresses: orm.Mapped[list['MemberAddress']] = orm.relationship('MemberAddress', back_populates='member', lazy='selectin')
    address_principal: orm.Mapped[Optional['MemberAddress']] = orm.relationship('MemberAddress',
                                                                                   primaryjoin="and_(Member.id==MemberAddress.member_id,MemberAddress.principal==True)",
                                                                                   lazy='selectin',
                                                                                   viewonly=True,)

    memberships: orm.Mapped[list['Membership']] = orm.relationship('Membership', back_populates='member', lazy='selectin')
    events: orm.Mapped[list['MemberEvent']] = orm.relationship('MemberEvent', back_populates='member', lazy='selectin')

#     logs: orm.Mapped[list['Log']] = orm.relationship('Log', foreign_keys='[Log.author]', back_populates='members', lazy='selectin')
#     logs_: orm.Mapped[list['Log']] = orm.relationship('Log', foreign_keys='[Log.updated_member]', back_populates='members_', lazy='selectin')

    @hybrid_property
    def current_season_has_subscribed(self):
        """ return true if member has subscribed to current season 
        """
        return any(m.is_in_current_season for m in self.memberships)

    @current_season_has_subscribed.expression
    def current_season_has_subscribed(cls):      #pylint: disable=no-self-argument   #function is a class factory
        """ SQL version
        """
        return  sa.select(
                    sa.case((sa.exists().where(
                    sa.and_(
                        Membership.member_id == cls.id,
                        Membership.is_in_current_season)).correlate(cls), True), else_=False,
                    ).label("current_season_has_subscribed")
                )

    @hybrid_property
    def current_season_presence_count(self):
        """ return number of presence in current season events 
        """
        return len([m.event for m in self.events if m.member_id == self.id and m.event.is_in_current_season])

    #TODO: code
    # @current_season_presence_count.expression
    # def current_season_presence_count(cls):      #pylint: disable=no-self-argument   #function is a class factory
    #     """ SQL version
    #     """
    #     return sa.select(MemberEvent.event,
    #             sa.func.count.select(
    #             sa.and_(
    #                     MemberEvent.member_id == cls.id,
    #                     Event.is_in_current_season)
    #             ).label("current_season_presence_count")).group_by().subquery()

    @hybrid_property
    def current_season_asso_role(self):
        """ return number of presence in current season events 
        """
        return len([m.event for m in self.events if m.member_id == self.id and m.event.is_in_current_season])

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        mbr_id = self.id
        mbr_creds = self.credential
        mbr_disc = self.discord_pseudo
        mbr_email = self.email_principal.email if self.email_principal else None
        mbr_address = self.address_principal.address if self.address_principal else None
        mbr_phone = self.phone_principal.phone if self.phone_principal else None

        mbr_asso_info = '' if self.current_season_has_subscribed else 'non ' #pylint: disable=using-constant-test #variable is not constant
        mbr_asso_info += f'cotisant, {self.current_season_presence_count} participation(s) cette saison.'

        match format_spec:
            case FormatTypes.RESTRICTED | FormatTypes.FULLSIMPLE:
                return ' - '.join([f'{x:{format_spec}}' for x in [mbr_id, mbr_creds, mbr_disc,] if x])

            case FormatTypes.FULLCOMPLETE:
                return '\n'.join([f'{x:{format_spec}}'for x in [mbr_id, mbr_creds, mbr_disc, mbr_email, mbr_address, mbr_phone,] if x]+[mbr_asso_info])

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')


class AssoRole(Base):
    """ Asso role table class
    """
    __tablename__ = 'asso_roles'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True, unique=True,)
    discord_roles: orm.Mapped[list['AssoRoleDiscordRole']] = orm.relationship('AssoRoleDiscordRole', back_populates='asso_role', lazy='selectin')
    members: orm.Mapped[list['MemberAssoRole']] = orm.relationship('MemberAssoRole', back_populates='asso_role', lazy='selectin')


class Membership(Base):
    """ Membership table class
    """
    __tablename__ = 'memberships'
    __table_args__ = (
        sa.UniqueConstraint('season_id', 'member_id',
                            comment='each member can have only one membership per season'),
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    date: orm.Mapped[HumanizedDate] = orm.mapped_column(SaHumanizedDate, nullable=False, comment='coupling between this and season')
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship('Member', back_populates='memberships', lazy='selectin')
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.id'), index=True, nullable=False)
    season: orm.Mapped['Season'] = orm.relationship('Season', back_populates='memberships', lazy='selectin')

    statutes_accepted: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)
    has_civil_insurance: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)
    picture_authorized: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)

    know_from_source_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('LUT_know_from_sources.id'), index=True, nullable=True)
    know_from_source: orm.Mapped[Optional['KnowFromSource']] = orm.relationship('KnowFromSource', back_populates='memberships', lazy='selectin')
    contribution_type_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('LUT_contribution_types.id'), index=True, nullable=False)
    contribution_type: orm.Mapped['ContributionType'] = orm.relationship('ContributionType', back_populates='memberships', lazy='selectin')
    # transactions: orm.Mapped[list['Transaction']] = orm.relationship('Transaction', back_populates='memberships')
    # logs: orm.Mapped[list['Log']] = orm.relationship('Log', back_populates='memberships', lazy='selectin')

    @hybrid_property
    def is_in_current_season(self):
        """ return true if item belongs to current season
        """
        return self.season.is_current_season

    @is_in_current_season.expression
    def is_in_current_season(cls):      #pylint: disable=no-self-argument   #function is a class factory
        """ SQL version
        """
        return  sa.select(
                    sa.case((sa.exists().where(
                    sa.and_(
                        Season.id == cls.season_id,
                        Season.is_current_season)).correlate(cls), True), else_=False,
                    ).label("is_in_current_season")
                ).scalar_subquery()

    #TODO: implement __str__ & __format__

@functools.total_ordering
class Event(Base):
    """ Event table class
    """
    __tablename__ = 'events'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    date: orm.Mapped[HumanizedDate] = orm.mapped_column(SaHumanizedDate, nullable=False, index=True)
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.id'), nullable=True, index=True)
    season: orm.Mapped['Season'] = orm.relationship('Season', back_populates='events', lazy='selectin')
    name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    description: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))

    members: orm.Mapped[list['MemberEvent']] = orm.relationship('MemberEvent', back_populates='event', lazy='selectin')
    # transactions: orm.Mapped[list['Transaction']] = orm.relationship('Transaction', back_populates='events', lazy='selectin')
    # logs: orm.Mapped[list['Log']] = orm.relationship('Log', back_populates='events', lazy='selectin')

    @hybrid_property
    def is_in_current_season(self):
        """ return true if item belongs to current season
        """
        return self.season.is_current_season

    @is_in_current_season.expression
    def is_in_current_season(cls):      #pylint: disable=no-self-argument   #function is a class factory
        """ SQL version
        """
        return  sa.select(
                    sa.case((sa.exists().where(
                    sa.and_(
                        Season.id == cls.season_id,
                        Season.is_current_season)).correlate(cls), True), else_=False,
                    ).label("is_in_current_season")
                ).scalar_subquery()

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.date == other.date

    def __lt__(self, other):
        return self.date < other.date

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.FULLSIMPLE | FormatTypes.FULLCOMPLETE | FormatTypes.RESTRICTED:
                return ' - '.join(f'{x}' for x in [self.date, self.name] if x)

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')



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
#     transactions: orm.Mapped[list['Transaction']] = orm.relationship('Transaction', back_populates='assets', lazy='selectin')


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

#     account_type: orm.Mapped['AccountType'] = orm.relationship('AccountType', back_populates='transactions', lazy='selectin')
#     assets: orm.Mapped[Optional['Asset']] = orm.relationship('Asset', back_populates='transactions', lazy='selectin')
#     events: orm.Mapped[Optional['Event']] = orm.relationship('Event', back_populates='transactions', lazy='selectin')
#     memberships: orm.Mapped[Optional['Membership']] = orm.relationship('Membership', back_populates='transactions', lazy='selectin')
#     seasons: orm.Mapped['Season'] = orm.relationship('Season', back_populates='transactions', lazy='selectin')
#     logs: orm.Mapped[list['Log']] = orm.relationship('Log', back_populates='transactions', lazy='selectin')


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

#     members: orm.Mapped['Member'] = orm.relationship('Member', foreign_keys=[author], back_populates='logs', lazy='selectin')
#     events: orm.Mapped[Optional['Event']] = orm.relationship('Event', back_populates='logs', lazy='selectin')
#     members_: orm.Mapped[Optional['Member']] = orm.relationship('Member', foreign_keys=[updated_member], back_populates='log_', lazy='selectin')
#     memberships: orm.Mapped[Optional['Membership']] = orm.relationship('Membership', back_populates='logs', lazy='selectin')
#     transactions: orm.Mapped[Optional['Transaction']] = orm.relationship('Transaction', back_populates='logs', lazy='selectin')



# Discord tables
#########################################

class DiscordRole(Base):
    """ Discord role table class
    """
    __tablename__ = 'discord_roles'

    id: orm.Mapped[int] = orm.mapped_column(sa.BigInteger, primary_key=True, index=True, unique=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    asso_roles: orm.Mapped[list['AssoRoleDiscordRole']] = orm.relationship('AssoRoleDiscordRole', back_populates='discord_role', lazy='selectin')

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.FULLCOMPLETE | FormatTypes.FULLSIMPLE | FormatTypes.RESTRICTED:
                return self.name

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')


class DiscordPseudo(Base):
    """ Discord pseudo table class
    """
    __tablename__ = 'discord_pseudos'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), unique=True, index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship('Member', back_populates='discord_pseudo', uselist=False, lazy='selectin')

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.FULLSIMPLE | FormatTypes.FULLCOMPLETE | FormatTypes.RESTRICTED:
                return '@' + self.name

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')



# Member private data tables
#########################################


@functools.total_ordering
class Credential(Base):
    """ user credential table class
    """
    __tablename__ = 'member_credentials'
    __table_args__ = (
                      sa.UniqueConstraint('first_name', 'last_name', 'birthdate'),
                      {'comment': 'contains RGPD info'},
                     )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    member: orm.Mapped[Optional['Member']] = orm.relationship('Member', back_populates='credential', uselist=False, lazy='selectin')
    first_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    last_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    birthdate: orm.Mapped[Optional[HumanizedDate]] = orm.mapped_column(SaHumanizedDate)

    @orm.reconstructor
    def __init__(self):
        self._fuzzy_lookup = None


    @property
    def fuzzy_lookup(self):
        """ Get the lookup value.
        """
        return self._fuzzy_lookup
    @fuzzy_lookup.setter
    def fuzzy_lookup(self, value):
        """ Set the lookup value.
        """
        self._fuzzy_lookup = value

    @property
    def fuzzy_match(self):
        """ return the matching percentage of credential against the lookup value
            if no lookup, return 100%
        """
        return 100 if not self._fuzzy_lookup else fuzz.token_sort_ratio(self._fuzzy_lookup, self.first_name + ' ' + self.last_name)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return ((self.last_name.lower(), self.first_name.lower()) ==
                (other.last_name.lower(), other.first_name.lower()))

    def __lt__(self, other):
        return ((self.last_name.lower(), self.first_name.lower()) <
                (other.last_name.lower(), other.first_name.lower()))

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        mbr_match = f'({self.fuzzy_match}%)' if self.fuzzy_match < 100 else None
        match format_spec:
            case FormatTypes.RESTRICTED:
                name_list = [self.first_name, mbr_match]

            case FormatTypes.FULLSIMPLE:
                name_list = [self.first_name, self.last_name, mbr_match]

            case FormatTypes.FULLCOMPLETE:
                name_list = [self.first_name, self.last_name, mbr_match, self.birthdate]

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')

        return ' '.join([f'{x}' for x in name_list if x])


class Email(Base):
    """ user email table class
    """
    __tablename__ = 'member_emails'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    address: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, unique=True, index=True)

    members: orm.Mapped[list['MemberEmail']] = orm.relationship('MemberEmail', back_populates='email', lazy='selectin')

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.RESTRICTED:
                return 'xxxxxx@yyyy.zzz'

            case FormatTypes.FULLSIMPLE | FormatTypes.FULLCOMPLETE:
                return self.address

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')


class Phone(Base):
    """ user phone number table class
    """
    __tablename__ = 'member_phones'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    number: orm.Mapped[str] = orm.mapped_column(sa.String(20), unique=True, index=True, nullable=False)

    members: orm.Mapped[list['MemberPhone']] = orm.relationship('MemberPhone', back_populates='phone', lazy='selectin')

    def __str__(self):
        return f'{self}'

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.RESTRICTED:
                return '(+33)000000000'

            case FormatTypes.FULLSIMPLE | FormatTypes.FULLCOMPLETE:
                return self.number

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')


class PostalAddress(Base):
    """ user address table class
    """
    __tablename__ = 'member_addresses'
    __table_args__ = (
        sa.UniqueConstraint('street_num', 'street_type_id', 'street_name', 'zip_code', 'city',),
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    street_num: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50), nullable=True)
    street_type_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('LUT_street_types.id'), index=True, nullable=True)
    street_type: orm.Mapped[Optional['StreetType']] = orm.relationship('StreetType', back_populates='addresses', lazy='selectin')
    street_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)
    zip_code: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer, nullable=True)
    city: orm.Mapped[str] = orm.mapped_column(sa.String(255), nullable=False)
    extra: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)

    members: orm.Mapped[list['MemberAddress']] = orm.relationship('MemberAddress', back_populates='address', lazy='selectin')

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.RESTRICTED:
                return self.city

            case FormatTypes.FULLSIMPLE | FormatTypes.FULLCOMPLETE:
                return ' '.join([f'{x}' for x in [self.street_num,
                                                  self.street_type,
                                                  self.street_name,
                                                  self.zip_code,
                                                  self.city,
                                                  self.extra] if x])

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')



# Junction tables
#########################################


class MemberEmail(Base):
    """ Junction table between members and emails
    """
    __tablename__ = 'JCT_member_email'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship('Member', back_populates='emails', lazy='selectin')
    email_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_emails.id'), index=True, nullable=False)
    email: orm.Mapped['Email'] = orm.relationship('Email', back_populates='members', lazy='selectin')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')


class MemberPhone(Base):
    """ Junction table between members and phones
    """
    __tablename__ = 'JCT_member_phone'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship('Member', back_populates='phones', lazy='selectin')
    phone_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_phones.id'), index=True, nullable=False)
    phone: orm.Mapped['Phone'] = orm.relationship('Phone', back_populates='members', lazy='selectin')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')


class MemberAddress(Base):
    """ Junction table between members and addresses
    """
    __tablename__ = 'JCT_member_address'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship('Member', back_populates='addresses', lazy='selectin')
    address_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_addresses.id'), index=True, nullable=False)
    address: orm.Mapped['PostalAddress'] = orm.relationship('PostalAddress', back_populates='members', lazy='selectin')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')


class MemberAssoRole(Base):
    """ Junction table between members and asso roles
    """
    __tablename__ = 'JCT_member_asso_role'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship('Member', back_populates='asso_roles', lazy='selectin')
    asso_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('asso_roles.id'), index=True, nullable=False)
    asso_role: orm.Mapped['AssoRole'] = orm.relationship('AssoRole', back_populates='members', lazy='selectin')
    start: orm.Mapped[HumanizedDate] = orm.mapped_column(SaHumanizedDate, nullable=False)
    end: orm.Mapped[Optional[HumanizedDate]] = orm.mapped_column(SaHumanizedDate, nullable=True)
    comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)


class AssoRoleDiscordRole(Base):
    """ Junction table between Asso and Discord roles
    """
    __tablename__ = 'JCT_asso_discord_role'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    asso_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('asso_roles.id'), index=True, nullable=False)
    asso_role: orm.Mapped['AssoRole'] = orm.relationship('AssoRole', back_populates='discord_roles', lazy='selectin')
    discord_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('discord_roles.id'), index=True, nullable=False)
    discord_role: orm.Mapped['DiscordRole'] = orm.relationship('DiscordRole', back_populates='asso_roles', lazy='selectin')


class MemberEvent(Base):
    """ Junction table between events and members
    """
    __tablename__ = 'JCT_event_member'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    event_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('events.id'), index=True, nullable=False)
    event: orm.Mapped['Event'] = orm.relationship('Event', back_populates='members', lazy='selectin')
    member_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=True, comment='Can be null name/id is lost.')
    member: orm.Mapped[Optional['Member']] = orm.relationship('Member', back_populates='events', lazy='selectin')
    presence: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=True, comment='if false: delegated vote')
    comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))





class AjDb():
    """ Context manager which manage AJ database
        Create DB engine and async session maker on enter, and dispose engine on exit
    """
    def __init__(self):
        self.db_engine = None
        self.AsyncSessionMaker = None   #pylint: disable=invalid-name   #variable is a class factory
        self.db_username = None

    async def __aenter__(self):
        #TODO clean this mess. I'm mixing db and session
        with AjConfig(save_on_exit=False, break_if_missing=True) as aj_config:
            self.db_username = aj_config.db_creds['user']
            # Connect to MariaDB Platform
            self.db_engine = aio_sa.create_async_engine("mysql+aiomysql://" + aj_config.db_connection_string,
                                                        echo=aj_config.db_echo)

        # aio_sa.async_sessionmaker: a factory for new AsyncSession objects
        # expire_on_commit - don't expire objects after transaction commit
        self.AsyncSessionMaker = aio_sa.async_sessionmaker(bind = self.db_engine, expire_on_commit=False)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        # for AsyncEngine created in function scope, close and
        # clean-up pooled connections
        await self.db_engine.dispose()
        self.db_username = None
        self.AsyncSessionMaker = None

    async def drop_create_schema(self):
        """ recreate database schema
        """
        if self.db_username != 'ajadmin':
            raise AjDbException(f"L'utilisateur {self.db_username} ne peut pas recréer la base de donnée !")
        # create all tables
        async with self.db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def search_member(self,
                     lookup_val = None,
                     match_crit = 50,
                     break_if_multi_perfect_match = True,):
        ''' retrieve list of member ids matching lookup_val which can be
                - discord member object
                - integer = member ID
                - string that is compared to "user friendly name" using fuzzy search

            for first 2 types, return exact match
            for last, return exact match if found, otherwise list of match above match_crit
            In case of multiple perfect match, raise exception if asked

            @return
                [member (if perfect match) or matchedMember (if not perfect match)]
        '''
        query = None
        # Check if lookup_val is a discord.Member object
        if isinstance(lookup_val, discord.Member):
            try:
                query = sa.select(Member).join(Member.discord_pseudo).where(DiscordPseudo.name == lookup_val.name)
            except MemberNotFound as e:
                raise AjDbException(f'Le champ de recherche {lookup_val} n\'est pas reconnu comme de type discord') from e

        # check if lookup_val is an integer (member ID)
        elif isinstance(lookup_val, int):
            query = sa.select(Member).where(Member.id == lookup_val)

        elif isinstance(lookup_val, str):
            query = sa.select(Member).where(Member.credential)

        else:
            raise AjDbException(f'Le champ de recherche doit être de type "discord", "int" or "str", pas "{type(lookup_val)}"')


        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        matched_members = query_result.scalars().all()

        if len(matched_members) <= 1:
            return matched_members

        # Fuzz search on credential
        for v in matched_members:
            v.credential.fuzzy_lookup = lookup_val

        perfect_match = [v for v in matched_members if v.credential.fuzzy_match == 100]
        if perfect_match:
            if len(perfect_match) > 1 and break_if_multi_perfect_match:
                raise AjDbException(f"Plusieurs correspondances parfaites pour {lookup_val}")
            return perfect_match

        matched_members = [v for v in matched_members if v.credential.fuzzy_match > match_crit]
        matched_members.sort(key=lambda x: x.credential.fuzzy_match, reverse=True)
        return matched_members

    async def get_seasons(self):
        ''' retrieve list of seasons

            @return
                [all found seasons]
        '''
        query = sa.select(Season)
        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        return query_result.scalars().all()

    async def get_season_subscribers(self, season_name = None):
        ''' retrieve list of member having subscribed to season
            @args
                season_name = Optional. If empty, use current season

            @return
                [all found Members]
        '''
        if season_name:
            query = sa.select(Member).join(Membership).join(Season).where(Season.name == season_name)
        else:
            query = sa.select(Member).join(Membership).where(Membership.is_in_current_season)
        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        return query_result.scalars().all()

    async def get_season_events(self, season_name = None):
        ''' retrieve list of events having occured in season
            @args
                season_name = Optional. If empty, use current season

            @return
                [all found events]
        '''
        if season_name:
            query = sa.select(Event).join(Season).where(Season.name == season_name)
        else:
            query = sa.select(Event).where(Event.is_in_current_season)
        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        return query_result.scalars().all()

    async def get_season_members(self, season_name = None):
        ''' retrieve list of members having participated in season
            @args
                season_name = Optional. If empty, use current season

            @return
                [all found members with number of presence]
        '''
        if season_name:
            query = sa.select(Member)\
                        .join(MemberEvent)\
                        .join(Event)\
                        .join(Season)\
                        .where(Season.name == season_name)\
                        .group_by(Member)
        else:
            query = sa.select(Member)\
                        .join(MemberEvent)\
                        .join(Event)\
                        .join(Season)\
                        .where(Season.is_current_season)\
                        .group_by(Member)

        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        return query_result.scalars().all()



if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
