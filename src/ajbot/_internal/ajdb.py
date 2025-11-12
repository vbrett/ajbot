''' manage AJ database

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
then manually reformated
'''
from typing import Optional
import datetime

import sqlalchemy as sa
from sqlalchemy.ext import asyncio as aio_sa
from sqlalchemy import orm

from thefuzz import fuzz
# import humanize
import discord
from discord.ext.commands import MemberNotFound

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import AjConfig, _AJ_ID_PREFIX



# class AjDate(datetime.date):
#     """ class that handles date type for AJ DB
#     """
#     def __new__(cls, indate, *args, **kwargs):
#         #check if first passed argument is already a datetime format
#         if isinstance(indate, (datetime.datetime, datetime.date)):
#             return super().__new__(cls, indate.year, indate.month, indate.day, *args, **kwargs)
#         if isinstance(indate, time):
#             return None
#         return super().__new__(cls, indate, *args, **kwargs)

#     def __format__(self, _):
#         humanize.i18n.activate("fr_FR")
#         return humanize.naturaldate(self)


class MemberId(int):
    """ Class that handles member id as integer, and represents it in with correct format
    """
    def __str__(self):
        return f"{_AJ_ID_PREFIX}{str(int(self)).zfill(5)}"


class Base(aio_sa.AsyncAttrs, orm.DeclarativeBase):
    """ Base ORM class
    """


# Lookup tables
################################


class LUTStreetTypes(Base):
    """ List of supported street types
    """
    __tablename__ = 'LUT_street_types'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    member_addresses: orm.Mapped[list['MemberAddresses']] = orm.relationship('MemberAddresses', back_populates='street_type')


class LUTContribution(Base):
    """ List of supported contribution levels
    """
    __tablename__ = 'LUT_contribution'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    memberships: orm.Mapped[list['Memberships']] = orm.relationship('Memberships', back_populates='contribution')


class LUTKnowFrom(Base):
    """ List of supported sources of knowing about the association
    """
    __tablename__ = 'LUT_know_from'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    memberships: orm.Mapped[list['Memberships']] = orm.relationship('Memberships', back_populates='know_from')


class LUTAccounts(Base):
    """ List of supported transaction accounts
    """
    __tablename__ = 'LUT_accounts'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    # transactions: orm.Mapped[list['Transactions']] = orm.relationship('Transactions', back_populates='LUT_accounts')


# Main tables
################################


class Seasons(Base):
    """ Seasons table class
    """
    __tablename__ = 'seasons'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(10), nullable=False, index=True)
    start: orm.Mapped[datetime.date] = orm.mapped_column(sa.Date, nullable=False)
    end: orm.Mapped[datetime.date] = orm.mapped_column(sa.Date, nullable=False)

    memberships: orm.Mapped[list['Memberships']] = orm.relationship('Memberships', back_populates='season')
    events: orm.Mapped[list['Events']] = orm.relationship('Events', back_populates='season')
    # transactions: orm.Mapped[list['Transactions']] = orm.relationship('Transactions', back_populates='seasons')


class Members(Base):
    """ Member table class
    """
    __tablename__ = 'members'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)

    credential_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('member_credentials.id'), index=True, nullable=True)
    credential: orm.Mapped[Optional['MemberCredentials']] = orm.relationship('MemberCredentials', back_populates='member', uselist=False, lazy='selectin')
    discord_pseudo_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('discord_pseudos.id'), index=True, nullable=True)
    discord_pseudo: orm.Mapped[Optional['DiscordPseudos']] = orm.relationship('DiscordPseudos', back_populates='member', uselist=False, lazy='selectin')
    JCT_member_asso_role: orm.Mapped[list['JCTMemberAssoRole']] = orm.relationship('JCTMemberAssoRole', back_populates='member', lazy='selectin')
    JCT_member_email: orm.Mapped[list['JCTMemberEmail']] = orm.relationship('JCTMemberEmail', back_populates='member', lazy='selectin')
    JCT_member_phone: orm.Mapped[list['JCTMemberPhone']] = orm.relationship('JCTMemberPhone', back_populates='member', lazy='selectin')
    JCT_member_address: orm.Mapped[list['JCTMemberAddress']] = orm.relationship('JCTMemberAddress', back_populates='member', lazy='selectin')

    memberships: orm.Mapped[list['Memberships']] = orm.relationship('Memberships', back_populates='member', lazy='selectin')
    JCT_event_member: orm.Mapped[list['JCTEventMember']] = orm.relationship('JCTEventMember', back_populates='member', lazy='selectin')

#     log: orm.Mapped[list['Log']] = orm.relationship('Log', foreign_keys='[Log.author]', back_populates='members')
#     log_: orm.Mapped[list['Log']] = orm.relationship('Log', foreign_keys='[Log.updated_member]', back_populates='members_')

    @orm.reconstructor
    def __init__(self):
        self.fuzz_match = None
        self.id = MemberId(self.id)

    def set_match(self, match_val):
        """ Set matching value (percentage) and return updated self
        """
        self.fuzz_match = match_val
        return self

    def __str__(self):
        return format(self, '')


    def __format__(self, format_spec):
        """ override format
        """
        mbr_id = str(self.id)
        mbr_creds = f'{self.credential:{format_spec}}' if self.credential else None
        mbr_disc = f'{self.discord_pseudo:{format_spec}}' if self.discord_pseudo else None
        mbr_match = f'({self.fuzz_match}% de correspondance)' if self.fuzz_match else None
        name_list = [
                        mbr_creds,
                        mbr_disc,
                        mbr_match,
                    ]
        match format_spec:
            case 'full':
                name_list = [mbr_id] + name_list

            case 'restricted' | '':
                pass

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')

        return ' - '.join([x for x in name_list if x])


class AssoRoles(Base):
    """ user member roles table class
    """
    __tablename__ = 'asso_roles'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True, unique=True,)
    JCT_asso_discord_role: orm.Mapped[list['JCTAssoDiscordRole']] = orm.relationship('JCTAssoDiscordRole', back_populates='asso_role')
    members: orm.Mapped[list['Members']] = orm.relationship('Members', back_populates='asso_role')
    JCT_member_asso_role: orm.Mapped[list['JCTMemberAssoRole']] = orm.relationship('JCTMemberAssoRole', back_populates='asso_role', lazy='selectin')


class Memberships(Base):
    """ Memberships table class
    """
    __tablename__ = 'memberships'
    __table_args__ = (
        sa.UniqueConstraint('season_id', 'member_id',
                            comment='each member can have only one membership per season'),
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    date: orm.Mapped[datetime.date] = orm.mapped_column(sa.Date, nullable=False, comment='coupling between this and season')
    member_id: orm.Mapped[MemberId] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='memberships')
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.id'), index=True, nullable=False)
    season: orm.Mapped['Seasons'] = orm.relationship('Seasons', back_populates='memberships')

    statutes_accepted: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)
    has_civil_insurance: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)
    picture_authorized: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)

    know_from_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('LUT_know_from.id'), index=True, nullable=True)
    know_from: orm.Mapped[Optional['LUTKnowFrom']] = orm.relationship('LUTKnowFrom', back_populates='memberships')
    contribution_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('LUT_contribution.id'), index=True, nullable=False)
    contribution: orm.Mapped['LUTContribution'] = orm.relationship('LUTContribution', back_populates='memberships')
    # transactions: orm.Mapped[list['Transactions']] = orm.relationship('Transactions', back_populates='memberships')
    # log: orm.Mapped[list['Log']] = orm.relationship('Log', back_populates='memberships')


class Events(Base):
    """ Events table class
    """
    __tablename__ = 'events'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    date: orm.Mapped[datetime.date] = orm.mapped_column(sa.Date, nullable=False, index=True)
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.id'), nullable=True, index=True)
    season: orm.Mapped['Seasons'] = orm.relationship('Seasons', back_populates='events')
    name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    description: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))

    JCT_event_member: orm.Mapped[list['JCTEventMember']] = orm.relationship('JCTEventMember', back_populates='event')
    # transactions: orm.Mapped[list['Transactions']] = orm.relationship('Transactions', back_populates='events')
    # log: orm.Mapped[list['Log']] = orm.relationship('Log', back_populates='events')


# class Assets(Base):
#     """ Assets table class
#     """
#     __tablename__ = 'assets'
#
#     id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
#     name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)
#     description: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))
#
#     transactions: orm.Mapped[list['Transactions']] = orm.relationship('Transactions', back_populates='assets')


# class Transactions(Base):
#     """ Transaction table class
#     """
#     __tablename__ = 'transaction'
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
#     date: orm.Mapped[datetime.date] = orm.mapped_column(sa.Date, nullable=False)
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

#     LUT_accounts: orm.Mapped['LUTAccounts'] = orm.relationship('LUTAccounts', back_populates='transactions')
#     assets: orm.Mapped[Optional['Assets']] = orm.relationship('Assets', back_populates='transactions')
#     events: orm.Mapped[Optional['Events']] = orm.relationship('Events', back_populates='transactions')
#     memberships: orm.Mapped[Optional['Memberships']] = orm.relationship('Memberships', back_populates='transactions')
#     seasons: orm.Mapped['Seasons'] = orm.relationship('Seasons', back_populates='transactions')
#     log: orm.Mapped[list['Log']] = orm.relationship('Log', back_populates='transactions')


# class Log(Base):
#     """ Log table class
#     """
#     __tablename__ = 'log'
#     __table_args__ = (
#         sa.ForeignKeyConstraint(['author_id'], ['members.id'], name='FK_members_TO_log1'),
#         sa.ForeignKeyConstraint(['updated_event_id'], ['events.id'], name='FK_events_TO_log'),
#         sa.ForeignKeyConstraint(['updated_member_id'], ['members.id'], name='FK_members_TO_log'),
#         sa.ForeignKeyConstraint(['updated_membership_id'], ['memberships.id'], name='FK_memberships_TO_log'),
#         sa.ForeignKeyConstraint(['updated_transaction_id'], ['transaction.id'], name='FK_transaction_TO_log'),
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

#     members: orm.Mapped['Members'] = orm.relationship('Members', foreign_keys=[author], back_populates='log')
#     events: orm.Mapped[Optional['Events']] = orm.relationship('Events', back_populates='log')
#     members_: orm.Mapped[Optional['Members']] = orm.relationship('Members', foreign_keys=[updated_member], back_populates='log_')
#     memberships: orm.Mapped[Optional['Memberships']] = orm.relationship('Memberships', back_populates='log')
#     transactions: orm.Mapped[Optional['Transactions']] = orm.relationship('Transactions', back_populates='log')



# Discord tables
#########################################

class DiscordRoles(Base):
    """ List of supported Discord roles
    """
    __tablename__ = 'discord_roles'

    id: orm.Mapped[int] = orm.mapped_column(sa.BigInteger, primary_key=True, index=True, unique=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    JCT_asso_discord_role: orm.Mapped[list['JCTAssoDiscordRole']] = orm.relationship('JCTAssoDiscordRole', back_populates='discord_role')


class DiscordPseudos(Base):
    """ user discord pseudo table class
    """
    __tablename__ = 'discord_pseudos'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), unique=True, index=True, nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='discord_pseudo', uselist=False)

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case 'full' |'restricted' | '':
                return f'@{self.name}'

            case _:
                return 'Ce format n\'est pas supporté'



# Members private data tables
#########################################


class MemberCredentials(Base):
    """ user credentials table class
    """
    __tablename__ = 'member_credentials'
    __table_args__ = (
                      sa.UniqueConstraint('first_name', 'last_name', 'birthdate'),
                      {'comment': 'contains RGPD info'},
                     )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    member: orm.Mapped[Optional['Members']] = orm.relationship('Members', back_populates='credential', uselist=False)
    first_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    last_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    birthdate: orm.Mapped[Optional[datetime.date]] = orm.mapped_column(sa.Date)

    def __str__(self):
        return format(self, '')

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case 'fullname':
                name_list = [self.first_name, self.last_name]

            case 'full':
                name_list = [self.first_name, self.last_name, self.birthdate]

            case 'restricted' | '':
                name_list = [self.first_name]

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')

        return ' '.join([x for x in name_list if x])


class MemberEmails(Base):
    """ user email table class
    """
    __tablename__ = 'member_emails'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    address: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, unique=True, index=True)

    JCT_member_email: orm.Mapped[list['JCTMemberEmail']] = orm.relationship('JCTMemberEmail', back_populates='email')


class MemberPhones(Base):
    """ user phone number table class
    """
    __tablename__ = 'member_phones'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    number: orm.Mapped[str] = orm.mapped_column(sa.String(20), unique=True, index=True, nullable=False)

    JCT_member_phone: orm.Mapped[list['JCTMemberPhone']] = orm.relationship('JCTMemberPhone', back_populates='phone')


class MemberAddresses(Base):
    """ user address table class
    """
    __tablename__ = 'member_addresses'
    __table_args__ = (
        sa.UniqueConstraint('street_num', 'street_type_id', 'street_name', 'zip_code', 'town',),
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    street_num: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50), nullable=True)
    street_type_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('LUT_street_types.id'), index=True, nullable=True)
    street_type: orm.Mapped[Optional['LUTStreetTypes']] = orm.relationship('LUTStreetTypes', back_populates='member_addresses')
    street_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)
    zip_code: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer, nullable=True)
    town: orm.Mapped[str] = orm.mapped_column(sa.String(255), nullable=False)
    street_extra: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)

    JCT_member_address: orm.Mapped[list['JCTMemberAddress']] = orm.relationship('JCTMemberAddress', back_populates='address')


# Junction tables
#########################################


class JCTMemberEmail(Base):
    """ Junction table between members and emails
    """
    __tablename__ = 'JCT_member_email'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='JCT_member_email')
    email_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_emails.id'), index=True, nullable=False)
    email: orm.Mapped['MemberEmails'] = orm.relationship('MemberEmails', back_populates='JCT_member_email')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')


class JCTMemberPhone(Base):
    """ Junction table between members and phones
    """
    __tablename__ = 'JCT_member_phone'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='JCT_member_phone')
    phone_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_phones.id'), index=True, nullable=False)
    phone: orm.Mapped['MemberPhones'] = orm.relationship('MemberPhones', back_populates='JCT_member_phone')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')


class JCTMemberAddress(Base):
    """ Junction table between members and addresses
    """
    __tablename__ = 'JCT_member_address'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='JCT_member_address')
    address_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_addresses.id'), index=True, nullable=False)
    address: orm.Mapped['MemberAddresses'] = orm.relationship('MemberAddresses', back_populates='JCT_member_address')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')


class JCTMemberAssoRole(Base):
    """ Junction table between members and asso roles
    """ 
    __tablename__ = 'JCT_member_asso_role'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='JCT_member_asso_role')
    asso_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('asso_roles.id'), index=True, nullable=False)
    asso_role: orm.Mapped['AssoRoles'] = orm.relationship('AssoRoles', back_populates='JCT_member_asso_role')
    start: orm.Mapped[datetime.date] = orm.mapped_column(sa.Date, nullable=False)
    end: orm.Mapped[Optional[datetime.date]] = orm.mapped_column(sa.Date, nullable=True)
    comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)


class JCTAssoDiscordRole(Base):
    """ Junction table between Asso and Discord roles
    """
    __tablename__ = 'JCT_asso_discord_role'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    asso_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('asso_roles.id'), index=True, nullable=False)
    asso_role: orm.Mapped['AssoRoles'] = orm.relationship('AssoRoles', back_populates='JCT_asso_discord_role')
    discord_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('discord_roles.id'), index=True, nullable=False)
    discord_role: orm.Mapped['DiscordRoles'] = orm.relationship('DiscordRoles', back_populates='JCT_asso_discord_role')


class JCTEventMember(Base):
    """ Junction table between events and members
    """
    __tablename__ = 'JCT_event_member'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    event_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('events.id'), index=True, nullable=False)
    event: orm.Mapped['Events'] = orm.relationship('Events', back_populates='JCT_event_member')
    member_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=True, comment='Can be null name/id is lost.')
    member: orm.Mapped[Optional['Members']] = orm.relationship('Members', back_populates='JCT_event_member')
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
                query = sa.select(Members).join(Members.discord_pseudo).where(DiscordPseudos.name == lookup_val.name)
            except MemberNotFound as e:
                raise AjDbException(f'Le champ de recherche {lookup_val} n\'est pas reconnu comme de type discord') from e

        # check if lookup_val is an integer (member ID)
        elif isinstance(lookup_val, int):
            query = sa.select(Members).where(Members.id == lookup_val)

        elif isinstance(lookup_val, str):
            query = sa.select(Members).where(Members.credential)

        else:
            raise AjDbException(f'Le champ de recherche doit être de type "discord", "int" or "str", pas "{type(lookup_val)}"')


        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        matched_members = query_result.scalars().all()

        if not isinstance(lookup_val, str):
            return matched_members

        # Fuzz search on credential
        fuzzy_match = [v.set_match(fuzz.token_sort_ratio(lookup_val, f'{v.credential:fullname}'))
                       for v in matched_members]
        fuzzy_match = [v for v in fuzzy_match if v.fuzz_match > match_crit]
        fuzzy_match.sort(key=lambda x: x.fuzz_match, reverse=True)

        perfect_match = [v.set_match(None) for v in fuzzy_match if v.fuzz_match == 100]
        if perfect_match:
            if len(perfect_match) > 1 and break_if_multi_perfect_match:
                raise AjDbException(f"multiple member perfectly match {lookup_val}")
            return perfect_match

        return fuzzy_match

#     def get_in_season_events(self, event_types = None):
#         """ returns events of certain type that are in current season
#         """
#         if event_types and not isinstance(event_types, list):
#             event_types = [event_types]

#         return [event for event in self if event.in_season and (not event_types or event.type in [etype for etype in event_types])]



if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
