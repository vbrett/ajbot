""" test deployment of a MariaDB instance

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
"""
import sys
import asyncio
from typing import Optional
from datetime import datetime, date #, time
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext import asyncio as aio_sa
from sqlalchemy import orm

from vbrpytools.dicjsontools import load_json_file

from ajbot._internal.config import AjConfig


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


class LUTDiscordRoles(Base):
    """ List of supported Discord roles
    """
    __tablename__ = 'LUT_discord_roles'

    id: orm.Mapped[int] = orm.mapped_column(sa.BigInteger, primary_key=True, index=True, unique=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    JCT_member_discord_role: orm.Mapped[list['JCTMemberDiscordRole']] = orm.relationship('JCTMemberDiscordRole', back_populates='discord_role')


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

    season_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(10), nullable=False, index=True)
    start: orm.Mapped[date] = orm.mapped_column(sa.Date, nullable=False)
    end: orm.Mapped[date] = orm.mapped_column(sa.Date, nullable=False)

    memberships: orm.Mapped[list['Memberships']] = orm.relationship('Memberships', back_populates='season')
    events: orm.Mapped[list['Events']] = orm.relationship('Events', back_populates='season')
    # transactions: orm.Mapped[list['Transactions']] = orm.relationship('Transactions', back_populates='seasons')


class Members(Base):
    """ Member table class
    """
    __tablename__ = 'members'

    member_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)

    credential_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('member_credentials.credential_id'), index=True, nullable=True)
    credential: orm.Mapped[Optional['MemberCredentials']] = orm.relationship('MemberCredentials', back_populates='member', uselist=False)
    discord_pseudo_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('member_discord_pseudos.discord_pseudo_id'), index=True, nullable=True)
    discord_pseudo: orm.Mapped[Optional['MemberDiscordPseudos']] = orm.relationship('MemberDiscordPseudos', back_populates='member', uselist=False)
    forced_role_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('member_roles.role_id'), index=True, nullable=True,
                                                                   comment='to override role defined by membership rules')
    forced_role:    orm.Mapped[Optional['MemberRoles']] = orm.relationship('MemberRoles', back_populates='members')
    JCT_member_email: orm.Mapped[list['JCTMemberEmail']] = orm.relationship('JCTMemberEmail', back_populates='member')
    JCT_member_phone: orm.Mapped[list['JCTMemberPhone']] = orm.relationship('JCTMemberPhone', back_populates='member')
    JCT_member_address: orm.Mapped[list['JCTMemberAddress']] = orm.relationship('JCTMemberAddress', back_populates='member')

    memberships: orm.Mapped[list['Memberships']] = orm.relationship('Memberships', back_populates='member')
    JCT_event_member: orm.Mapped[list['JCTEventMember']] = orm.relationship('JCTEventMember', back_populates='member')

#     log: orm.Mapped[list['Log']] = orm.relationship('Log', foreign_keys='[Log.author]', back_populates='members')
#     log_: orm.Mapped[list['Log']] = orm.relationship('Log', foreign_keys='[Log.updated_member]', back_populates='members_')


class Memberships(Base):
    """ Memberships table class
    """
    __tablename__ = 'memberships'
    __table_args__ = (
        sa.UniqueConstraint('season_id', 'member_id',
                            comment='each member can have only one membership per season'),
    )

    membership_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    membership_date: orm.Mapped[date] = orm.mapped_column(sa.Date, nullable=False, comment='coupling between this and season')
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.member_id'), index=True, nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='memberships')
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.season_id'), index=True, nullable=False)
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

    event_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    event_date: orm.Mapped[date] = orm.mapped_column(sa.Date, nullable=False, index=True)
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.season_id'), nullable=True, comment='shall be computed based on event_date', index=True)
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
#     asset_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
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
#         sa.ForeignKeyConstraint(['associated_asset'], ['assets.asset_id'], name='FK_assets_TO_transaction'),
#         sa.ForeignKeyConstraint(['associated_event'], ['events.event_id'], name='FK_events_TO_transaction'),
#         sa.ForeignKeyConstraint(['associated_membership'], ['memberships.membership_id'], name='FK_memberships_TO_transaction'),
#         sa.Index('FK_LUT_accounts_TO_transaction', 'account'),
#         sa.Index('FK_assets_TO_transaction', 'associated_asset'),
#         sa.Index('FK_events_TO_transaction', 'associated_event'),
#         sa.Index('FK_memberships_TO_transaction', 'associated_membership'),
#         sa.Index('UQ_transaction_id', 'transaction_id', unique=True)
#     )

#     transaction_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, comment='UUID')
#     transaction_date: orm.Mapped[date] = orm.mapped_column(sa.Date, nullable=False)
#     season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.season_id'), nullable=False, comment='shall be computed based on transaction_date', index=True)
#     account: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
#     associated_event: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     associated_asset: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     associated_membership: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     title: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50), comment='non empty only if all associated_xxx are empty')
#     details: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(100))
#     credit: orm.Mapped[Optional[float]] = orm.mapped_column(sa.Float)
#     debit: orm.Mapped[Optional[float]] = orm.mapped_column(sa.Float)
#     comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(100))

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
#         sa.ForeignKeyConstraint(['author'], ['members.member_id'], name='FK_members_TO_log1'),
#         sa.ForeignKeyConstraint(['updated_event'], ['events.event_id'], name='FK_events_TO_log'),
#         sa.ForeignKeyConstraint(['updated_member'], ['members.member_id'], name='FK_members_TO_log'),
#         sa.ForeignKeyConstraint(['updated_membership'], ['memberships.membership_id'], name='FK_memberships_TO_log'),
#         sa.ForeignKeyConstraint(['updated_transaction'], ['transaction.transaction_id'], name='FK_transaction_TO_log'),
#         sa.Index('FK_events_TO_log', 'updated_event'),
#         sa.Index('FK_members_TO_log', 'updated_member'),
#         sa.Index('FK_members_TO_log1', 'author'),
#         sa.Index('FK_memberships_TO_log', 'updated_membership'),
#         sa.Index('FK_transaction_TO_log', 'updated_transaction'),
#         sa.Index('UQ_datetime', 'log_datetime', unique=True)
#     )

#     log_datetime: orm.Mapped[datetime] = orm.mapped_column(sa.DateTime, primary_key=True)
#     author: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
#  ?  name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
#     comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))
#     updated_event: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     updated_membership: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     updated_member: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     updated_transaction: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)

#     members: orm.Mapped['Members'] = orm.relationship('Members', foreign_keys=[author], back_populates='log')
#     events: orm.Mapped[Optional['Events']] = orm.relationship('Events', back_populates='log')
#     members_: orm.Mapped[Optional['Members']] = orm.relationship('Members', foreign_keys=[updated_member], back_populates='log_')
#     memberships: orm.Mapped[Optional['Memberships']] = orm.relationship('Memberships', back_populates='log')
#     transactions: orm.Mapped[Optional['Transactions']] = orm.relationship('Transactions', back_populates='log')



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

    credential_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    member: orm.Mapped[Optional['Members']] = orm.relationship('Members', back_populates='credential', uselist=False)
    first_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    last_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    birthdate: orm.Mapped[Optional[date]] = orm.mapped_column(sa.Date)


class MemberRoles(Base):
    """ user member roles table class
    """
    __tablename__ = 'member_roles'

    role_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True, unique=True,)
    JCT_member_discord_role: orm.Mapped[list['JCTMemberDiscordRole']] = orm.relationship('JCTMemberDiscordRole', back_populates='member_role')
    members: orm.Mapped[list['Members']] = orm.relationship('Members', back_populates='forced_role')


class MemberDiscordPseudos(Base):
    """ user discord pseudo table class
    """
    __tablename__ = 'member_discord_pseudos'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    discord_pseudo_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    discord_pseudo:  orm.Mapped[str] = orm.mapped_column(sa.String(50), unique=True, index=True, nullable=False)
    member:          orm.Mapped['Members'] = orm.relationship('Members', back_populates='discord_pseudo', uselist=False)


class MemberEmails(Base):
    """ user email table class
    """
    __tablename__ = 'member_emails'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    email_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    email: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, unique=True, index=True)

    JCT_member_email: orm.Mapped[list['JCTMemberEmail']] = orm.relationship('JCTMemberEmail', back_populates='email')


class MemberPhones(Base):
    """ user phone number table class
    """
    __tablename__ = 'member_phones'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    phone_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    phone_number: orm.Mapped[str] = orm.mapped_column(sa.String(20), unique=True, index=True, nullable=False)

    JCT_member_phone: orm.Mapped[list['JCTMemberPhone']] = orm.relationship('JCTMemberPhone', back_populates='phone')


class MemberAddresses(Base):
    """ user address table class
    """
    __tablename__ = 'member_addresses'
    __table_args__ = (
        sa.UniqueConstraint('street_num', 'street_type_id', 'street_name', 'zip_code', 'town',),
        {'comment': 'contains RGPD info'}
    )

    address_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
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
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.member_id'), index=True, nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='JCT_member_email')
    email_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_emails.email_id'), index=True, nullable=False)
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
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.member_id'), index=True, nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='JCT_member_phone')
    phone_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_phones.phone_id'), index=True, nullable=False)
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
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.member_id'), index=True, nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='JCT_member_address')
    address_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_addresses.address_id'), index=True, nullable=False)
    address: orm.Mapped['MemberAddresses'] = orm.relationship('MemberAddresses', back_populates='JCT_member_address')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')


class JCTMemberDiscordRole(Base):
    """ Junction table between members and Discord roles
    """
    __tablename__ = 'JCT_member_discord_role'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_roles.role_id'), index=True, nullable=False)
    member_role: orm.Mapped['MemberRoles'] = orm.relationship('MemberRoles', back_populates='JCT_member_discord_role')
    discord_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('LUT_discord_roles.id'), index=True, nullable=False)
    discord_role: orm.Mapped['LUTDiscordRoles'] = orm.relationship('LUTDiscordRoles', back_populates='JCT_member_discord_role')


class JCTEventMember(Base):
    """ Junction table between events and members
    """
    __tablename__ = 'JCT_event_member'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    event_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('events.event_id'), index=True, nullable=False)
    event: orm.Mapped['Events'] = orm.relationship('Events', back_populates='JCT_event_member')
    member_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('members.member_id'), index=True, nullable=True, comment='Can be null name/id is lost.')
    member: orm.Mapped[Optional['Members']] = orm.relationship('Members', back_populates='JCT_event_member')
    presence: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=True, comment='if false: delegated vote')
    comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(100))















async def _create_db():
    """ main function - async version
    """
    with AjConfig(break_if_missing=True,
                  save_on_exit=False,
                 ) as aj_config:

        # Connect to MariaDB Platform
        db_engine = aio_sa.create_async_engine("mysql+aiomysql://" + aj_config.db_connection_string,
                                               echo=True)

        # aio_sa.async_sessionmaker: a factory for new AsyncSession objects
        # expire_on_commit - don't expire objects after transaction commit
        async_session = aio_sa.async_sessionmaker(bind = db_engine, expire_on_commit=False)


        # create all tables
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        # Populate all tables

        # fill lookup tables
        lut_tables = []
        xsldb_lookup_tables = load_json_file(Path('aj_xls2db/xlsdb_LUP.json'))
        for val in xsldb_lookup_tables['saisons']:
            lut_tables.append(Seasons(name=val['nom'],
                                        start=datetime.fromisoformat(val['debut']).date(),
                                        end=datetime.fromisoformat(val['fin']).date()))
        for val in xsldb_lookup_tables['contribution']:
            lut_tables.append(LUTContribution(name=val['val']))
        for val in xsldb_lookup_tables['connaissance']:
            lut_tables.append(LUTKnowFrom(name=val['val']))
        for val in xsldb_lookup_tables['compte']:
            lut_tables.append(LUTAccounts(name=val['val']))
        for val in xsldb_lookup_tables['type_voie']:
            lut_tables.append(LUTStreetTypes(name=val['val']))
        for val in xsldb_lookup_tables['discord_role']:
            lut_tables.append(LUTDiscordRoles(name=val['val'],
                                                id=int(val['id']),))
        for val in xsldb_lookup_tables['roles']:
            new_member_role = MemberRoles(name=val['asso'])
            lut_tables.append(new_member_role)
            if val.get('discord'):
                for d_role in val['discord'].split(','):
                    matched_role = [elt for elt in lut_tables
                                    if isinstance(elt, LUTDiscordRoles) and elt.name == d_role]
                    lut_tables.append(JCTMemberDiscordRole(member_role=new_member_role,
                                                            discord_role=matched_role[0]))

        async with async_session() as session:
            async with session.begin():
                session.add_all(lut_tables)

        # Fill member tables
        member_tables = []
        xsldb_lut_member = load_json_file(Path('aj_xls2db/xlsdb_membres.json'))
        for val in xsldb_lut_member['annuaire']:
            try:
                _creation_date = datetime.fromisoformat(val['creation']['date'])
            except ValueError:
                continue
            new_member = Members(member_id=int(val['id']))
            member_tables.append(new_member)

            if val.get('pseudo_discord'):
                new_member.discord_pseudo=MemberDiscordPseudos(discord_pseudo=val['pseudo_discord'])

            if val.get('saison'):
                if val['saison'].get('asso_role_manuel'):
                    matched_role = [elt for elt in lut_tables
                                    if isinstance(elt, MemberRoles) and elt.name == val['saison']['asso_role_manuel']]
                    new_member.forced_role = matched_role[0]

            if val.get('prenom') or val.get('nom') or val.get('date_naissance'):
                new_member.credential = MemberCredentials(first_name=val.get('prenom'),
                                                    last_name=val.get('nom'))
                if val.get('date_naissance'):
                    new_member.credential.birthdate = datetime.fromisoformat(val['date_naissance']).date()

            if val.get('emails'):
                principal = True
                for single_rpg in val['emails'].split(';'):
                    matched_rpg = [elt for elt in member_tables
                                if isinstance(elt, MemberEmails) and elt.email == single_rpg]
                    if matched_rpg:
                        new_rpg = matched_rpg[0]
                    else:
                        new_rpg = MemberEmails(email=single_rpg)
                        member_tables.append(new_rpg)
                    new_jct = JCTMemberEmail(member=new_member,
                                            email=new_rpg,
                                            principal=principal)
                    principal = False
                    member_tables.append(new_jct)

            if val.get('telephone'):
                single_rpg = f"(+33){val['telephone']:9d}"
                matched_rpg = [elt for elt in member_tables
                                if isinstance(elt, MemberPhones) and elt.phone_number == single_rpg]
                if matched_rpg:
                    new_rpg = matched_rpg[0]
                else:
                    new_rpg = MemberPhones(phone_number=single_rpg)
                    member_tables.append(new_rpg)
                new_jct = JCTMemberPhone(member=new_member,
                                        phone=new_rpg,
                                        principal=True)
                member_tables.append(new_jct)

            if val.get('adresse'):
                matched_rpg = False
                matched_rpg = [elt for elt in member_tables
                                if     isinstance(elt, MemberAddresses)
                                and elt.street_num == val['adresse'].get('numero')
                                and elt.street_name == val['adresse'].get('nom_voie')
                                and (not elt.street_type
                                        or elt.street_type.name == val['adresse'].get('type_voie')
                                        )
                                and elt.zip_code == val['adresse'].get('cp')
                                and elt.town == val['adresse'].get('ville')
                            ]
                if matched_rpg:
                    new_rpg = matched_rpg[0]
                else:
                    new_rpg = MemberAddresses()
                    new_rpg.town=val['adresse']['ville']
                    if val['adresse'].get('numero'):
                        new_rpg.street_num = val['adresse']['numero']
                    if val['adresse'].get('type_voie'):
                        matched_type_voie = [elt for elt in lut_tables
                                        if isinstance(elt, LUTStreetTypes) and elt.name == val['adresse']['type_voie']]
                        new_rpg.street_type = matched_type_voie[0]
                    if val['adresse'].get('autre'):
                        new_rpg.street_extra = val['adresse']['autre']
                    if val['adresse'].get('nom_voie'):
                        new_rpg.street_name = val['adresse']['nom_voie']
                    if val['adresse'].get('cp'):
                        new_rpg.zip_code = val['adresse']['cp']
                    member_tables.append(new_rpg)

                new_jct = JCTMemberAddress(member=new_member,
                                        address=new_rpg,
                                        principal=True)
                member_tables.append(new_jct)

        async with async_session() as session:
            async with session.begin():
                session.add_all(member_tables)

        # fill membership tables
        membership_tables = []
        xsldb_events = load_json_file(Path('aj_xls2db/xlsdb_suivi.json'))
        for val in [event for event in xsldb_events['suivi'] if event['entree']['categorie'] == 'Cotisation']:
            new_membership = Memberships()
            membership_tables.append(new_membership)
            new_membership.membership_date = datetime.fromisoformat(val['date']).date()
            new_membership.season       = [elt for elt in lut_tables    if isinstance(elt, Seasons        ) and elt.name      == val['entree']['nom']][0]
            new_membership.member       = [elt for elt in member_tables if isinstance(elt, Members        ) and elt.member_id == val['membre']['id']][0]
            new_membership.contribution = [elt for elt in lut_tables    if isinstance(elt, LUTContribution) and elt.name      == val['cotisation']][0]
            if val['membre'].get('prive'):
                new_membership.statutes_accepted = val['membre']['prive'].get('approbation_statuts', '').lower() == 'oui'
                new_membership.has_civil_insurance = val['membre']['prive'].get('assurance_resp_civile', '').lower() == 'oui'
                new_membership.picture_authorized = val['membre']['prive'].get('utilisation_image', '').lower() == 'oui'
            if val['membre'].get('source_connaissance'):
                new_membership.know_from = [elt for elt in lut_tables if isinstance(elt, LUTKnowFrom) and elt.name == val['membre']['source_connaissance']][0]

        async with async_session() as session:
            async with session.begin():
                session.add_all(membership_tables)

        # fill event tables
        event_tables = []
        for val in [event for event in xsldb_events['suivi'] if event['entree']['categorie'] == 'Evènement'
                                                               and not event['entree'].get('detail')]:
            new_event = Events()
            event_tables.append(new_event)
            new_event.event_date = datetime.fromisoformat(val['date']).date()
            new_event.season     = [elt for elt in lut_tables    if isinstance(elt, Seasons        ) and new_event.event_date >= elt.start
                                                                                                       and new_event.event_date <= elt.end][0]
            new_event.name       = val['entree']['nom']

        for val in [event for event in xsldb_events['suivi'] if (event['entree']['categorie'] == 'Evènement'
                                                               and event['entree'].get('detail') == 'Vote par pouvoir')
                                                               or(event['entree']['categorie'] == 'Présence')]:
            new_event = JCTEventMember()
            event_tables.append(new_event)
            new_event.presence = val['entree']['categorie'] == 'Présence'
            matched_event = [elt for elt in event_tables if isinstance(elt, Events) and elt.event_date == datetime.fromisoformat(val['date']).date()]
            if matched_event:
                new_event.event = matched_event[0]
            else:
                new_event.event = Events()
                event_tables.append(new_event.event)
                new_event.event.event_date = datetime.fromisoformat(val['date']).date()
                new_event.event.season     = [elt for elt in lut_tables    if isinstance(elt, Seasons) and new_event.event.event_date >= elt.start
                                                                                                       and new_event.event.event_date <= elt.end][0]
            if val.get('membre'):
                new_event.member = [elt for elt in member_tables if isinstance(elt, Members        ) and elt.member_id == val['membre']['id']][0]

            if val.get('commentaire_old'):
                new_event.comment = val['commentaire_old']

        async with async_session() as session:
            async with session.begin():
                session.add_all(event_tables)


        # async with async_session.begin() as session:
        #     query = sa.select(Users).options(orm.selectinload(Users.member_emails)).limit(1)
        #     query_result = await session.execute(query)
        #     for qr in query_result.scalars():
        #         print(qr)

        # for AsyncEngine created in function scope, close and
        # clean-up pooled connections
        await db_engine.dispose()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_create_db()))
