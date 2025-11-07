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


class LUTDiscordRoles(Base):
    """ List of supported Discord roles
    """
    __tablename__ = 'LUT_discord_roles'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    members: orm.Mapped[list['Members']] = orm.relationship('Members', back_populates='discord_roles')


# class LUTAccounts(Base):
#     """ List of supported transaction accounts
#     """
#     __tablename__ = 'LUT_accounts'
#
#     id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
#     name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)
#
#     transactions: orm.Mapped[list['Transactions']] = orm.relationship('Transactions', back_populates='LUT_accounts')
#
#
# class LUTContribution(Base):
#     """ List of supported contribution levels
#     """
#     __tablename__ = 'LUT_contribution'
#
#     id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
#     name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)
#
#     memberships: orm.Mapped[list['Memberships']] = orm.relationship('Memberships', back_populates='LUT_contribution')
#
#
# class LUTKnowFrom(Base):
#     """ List of supported sources of knowing about the association
#     """
#     __tablename__ = 'LUT_know_from'
#
#     id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
#     name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)
#
#     memberships: orm.Mapped[list['Memberships']] = orm.relationship('Memberships', back_populates='LUT_know_from')
#
#
# class LUTStreetTypes(Base):
#     """ List of supported street types
#     """
#     __tablename__ = 'LUT_street_types'
#
#     id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
#     name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)
#
#     addresses: orm.Mapped[list['Addresses']] = orm.relationship('Addresses', back_populates='LUT_street_types')


# Main tables
################################


class Members(Base):
    """ Member table class
    """
    __tablename__ = 'members'

    member_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    discord_role_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('LUT_discord_roles.id'), nullable=True, comment='to override role defined by membership rules', index=True)
    discord_roles: orm.Mapped['LUTDiscordRoles'] = orm.relationship('LUTDiscordRoles', back_populates='members')
    discord_pseudo: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50), nullable=True, unique=True, index=True)

    credential_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('credentials.credential_id'), index=True)
    credential: orm.Mapped[Optional['Credentials']] = orm.relationship('Credentials', back_populates='member', uselist=False)
    JCT_member_email: orm.Mapped[list['JCTMemberEmail']] = orm.relationship('JCTMemberEmail', back_populates='member')
#     JCT_member_address: orm.Mapped[list['JCTMemberAddress']] = orm.relationship('JCTMemberAddress', back_populates='member')
#     JCT_member_phone: orm.Mapped[list['JCTMemberPhone']] = orm.relationship('JCTMemberPhone', back_populates='member')
#
#     memberships: orm.Mapped[list['Memberships']] = orm.relationship('Memberships', back_populates='member')

    comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)
#
#     JCT_event_member: orm.Mapped[list['JCTEventMember']] = orm.relationship('JCTEventMember', back_populates='members')
#     log: orm.Mapped[list['Log']] = orm.relationship('Log', foreign_keys='[Log.author]', back_populates='members')
#     log_: orm.Mapped[list['Log']] = orm.relationship('Log', foreign_keys='[Log.updated_member]', back_populates='members_')


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
#
#
# class Seasons(Base):
#     """ Seasons table class
#     """
#     __tablename__ = 'seasons'
#
#     season_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
#     name: orm.Mapped[str] = orm.mapped_column(sa.String(10), nullable=False, index=True)
#     start: orm.Mapped[date] = orm.mapped_column(sa.Date, nullable=False)
#     end: orm.Mapped[date] = orm.mapped_column(sa.Date, nullable=False)
#
#     events: orm.Mapped[list['Events']] = orm.relationship('Events', back_populates='seasons')
#     memberships: orm.Mapped[list['Memberships']] = orm.relationship('Memberships', back_populates='seasons')
#     transactions: orm.Mapped[list['Transactions']] = orm.relationship('Transactions', back_populates='seasons')
#
#
# class Events(Base):
#     """ Events table class
#     """
#     __tablename__ = 'events'
#
#     event_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True)
#     event_date: orm.Mapped[date] = orm.mapped_column(sa.Date, nullable=False, index=True)
#     season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.season_id'), nullable=True, comment='shall be computed based on event_date', index=True)
#     seasons: orm.Mapped['Seasons'] = orm.relationship('Seasons', back_populates='events')
#     name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
#     description: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))
#
#     JCT_event_member: orm.Mapped[list['JCTEventMember']] = orm.relationship('JCTEventMember', back_populates='events')
#     transactions: orm.Mapped[list['Transactions']] = orm.relationship('Transactions', back_populates='events')
#     log: orm.Mapped[list['Log']] = orm.relationship('Log', back_populates='events')
#
#
# class Memberships(Base):
#     """ Memberships table class
#     """
#     __tablename__ = 'memberships'
#     __table_args__ = (
#         sa.UniqueConstraint('season_id', 'member_id', name='UQ_season_member',
#                             comment='each member can have only one membership per season'),
#     )
#
#     membership_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)
#     membership_date: orm.Mapped[date] = orm.mapped_column(sa.Date, nullable=False, comment='coupling between this and season')
#     season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.season_id'), nullable=False, index=True)
#     seasons: orm.Mapped['Seasons'] = orm.relationship('Seasons', back_populates='memberships')
#     member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.member_id'), index=True, nullable=False)
#     member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='memberships')
#     contribution_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('LUT_contribution.id'), index=True, nullable=False)
#     LUT_contribution: orm.Mapped['LUTContribution'] = orm.relationship('LUTContribution', back_populates='memberships')
#     picture_authorized: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False)
#     statutes_accepted: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False)
#     civil_insurance: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False)
#     know_from: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey(['LUT_know_from.id']), index=True)
#     LUT_know_from: orm.Mapped[Optional['LUTKnowFrom']] = orm.relationship('LUTKnowFrom', back_populates='memberships')
#     transactions: orm.Mapped[list['Transactions']] = orm.relationship('Transactions', back_populates='memberships')
#     log: orm.Mapped[list['Log']] = orm.relationship('Log', back_populates='memberships')


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
#     name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
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


class Credentials(Base):
    """ user credentials table class
    """
    __tablename__ = 'credentials'
    __table_args__ = (
        {'comment': 'contain RGPD info'},
        # sa.UniqueConstraint('first_name', 'last_name', 'birthdate', name='UQ_credential_identity',)
    )

    credential_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    member: orm.Mapped[Optional['Members']] = orm.relationship('Members', back_populates='credential', uselist=False)
    first_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    last_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    birthdate: orm.Mapped[Optional[date]] = orm.mapped_column(sa.Date)


class Emails(Base):
    """ user email table class
    """
    __tablename__ = 'emails'
    __table_args__ = (
        {'comment': 'contain RGPD info'}
    )

    email_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    email: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, unique=True, index=True)

    JCT_member_email: orm.Mapped[list['JCTMemberEmail']] = orm.relationship('JCTMemberEmail', back_populates='email')


# class Phones(Base):
#     """ user phone number table class
#     """
#     __tablename__ = 'phones'
#     __table_args__ = (
#         sa.Index('UQ_phone_id', 'phone_id', unique=True),
#         sa.Index('UQ_phone_number', 'phone_number', unique=True),
#         {'comment': 'contain RGPD info'}
#     )

#     phone_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, comment='UUID')
#     phone_number: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False)

#     JCT_member_phone: orm.Mapped[list['JCTMemberPhone']] = orm.relationship('JCTMemberPhone', back_populates='phone')


# class Addresses(Base):
#     """ user address table class
#     """
#     __tablename__ = 'addresses'
#     __table_args__ = (
#         sa.ForeignKeyConstraint(['street_type'], ['LUT_street_types.id'], name='FK_LUT_street_types_TO_addresses'),
#         sa.Index('FK_LUT_street_types_TO_addresses', 'street_type'),
#         sa.Index('UQ_address_id', 'address_id', unique=True),
#         {'comment': 'contain RGPD info'}
#     )

#     address_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, comment='UUID')
#     street_num: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
#     street_type: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     street_extra: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))
#     street_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))
#     zip_code: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer)
#     town: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))
#     other: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))

#     LUT_street_types: orm.Mapped[Optional['LUTStreetTypes']] = orm.relationship('LUTStreetTypes', back_populates='addresses')
#     JCT_member_address: orm.Mapped[list['JCTMemberAddress']] = orm.relationship('JCTMemberAddress', back_populates='address')


# Junction tables
#########################################


class JCTMemberEmail(Base):
    """ Junction table between members and emails
    """
    __tablename__ = 'JCT_member_email'
    __table_args__ = (
        {'comment': 'contain RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.member_id'), nullable=False)
    member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='JCT_member_email')
    email_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('emails.email_id'), nullable=False)
    email: orm.Mapped['Emails'] = orm.relationship('Emails', back_populates='JCT_member_email')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')



# class JCTEventMember(Base):
#     """ Junction table between events and members
#     """
#     __tablename__ = 'JCT_event_member'
#     __table_args__ = (
#         sa.ForeignKeyConstraint(['event'], ['events.event_id'], name='FK_events_TO_JCT_event_member'),
#         sa.ForeignKeyConstraint(['member'], ['members.member_id'], name='FK_members_TO_JCT_event_member'),
#         sa.Index('FK_events_TO_JCT_event_member', 'event'),
#         sa.Index('FK_members_TO_JCT_event_member', 'member'),
#         sa.Index('UQ_id', 'id', unique=True)
#     )
#
#     id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, comment='UUID')
#     event: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
#     presence: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=True, comment='if false: delegating vote')
#     member: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer, comment='Can be null name/id is lost.')
#     comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(100))
#
#     events: orm.Mapped['Events'] = orm.relationship('Events', back_populates='JCT_event_member')
#     members: orm.Mapped[Optional['Members']] = orm.relationship('Members', back_populates='JCT_event_member')
#
#
# class JCTMemberAddress(Base):
#     """ Junction table between members and addresses
#     """
#     __tablename__ = 'JCT_member_address'
#     __table_args__ = (
#         sa.ForeignKeyConstraint(['address_id'], ['addresses.address_id'], name='FK_addresses_TO_JCT_member_address'),
#         sa.ForeignKeyConstraint(['member_id'], ['members.member_id'], name='FK_members_TO_JCT_member_address'),
#         sa.Index('FK_addresses_TO_JCT_member_address', 'address_id'),
#         sa.Index('FK_members_TO_JCT_member_address', 'member_id'),
#         sa.Index('UQ_id', 'id', unique=True),
#         {'comment': 'contain RGPD info'}
#     )
#
#     id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, comment='UUID')
#     member_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
#     address_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
#     principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')
#
#     address: orm.Mapped['Addresses'] = orm.relationship('Addresses', back_populates='JCT_member_address')
#     member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='JCT_member_address')
#
#
# class JCTMemberPhone(Base):
#     """ Junction table between members and phones
#     """
#     __tablename__ = 'JCT_member_phone'
#     __table_args__ = (
#         sa.ForeignKeyConstraint(['member_id'], ['members.member_id'], name='FK_members_TO_JCT_member_phone'),
#         sa.ForeignKeyConstraint(['phone_id'], ['phones.phone_id'], name='FK_phones_TO_JCT_member_phone'),
#         sa.Index('FK_members_TO_JCT_member_phone', 'member_id'),
#         sa.Index('FK_phones_TO_JCT_member_phone', 'phone_id'),
#         sa.Index('UQ_id', 'id', unique=True),
#         {'comment': 'contain RGPD info'}
#     )
#
#     id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, comment='UUID')
#     member_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
#     phone_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
#     principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')
#
#     member: orm.Mapped['Members'] = orm.relationship('Members', back_populates='JCT_member_phone')
#     phone: orm.Mapped['Phones'] = orm.relationship('Phones', back_populates='JCT_member_phone')


async def _create_db():
    """ main function - async version
    """
    with AjConfig(break_if_missing=True,
                  save_on_exit=False,       #TODO: change to True
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

        # # init lookup tables
        # xsldb_lut_season = load_json_file(Path('tests/xlsdb_LUP_saison.json'))
        # async with async_session.begin() as session:
        #     for val in ['Membre','Membre saison préc','Artisan',
        #                 'Bureau - Communication', 'Bureau - Président','Bureau - Secrétaire',
        #                 'Bureau - Trésorier','Bureau - Autre', 'Bureau - Admin',
        #                 'ProBot ✨','Simple Poll','VbrBot']:
        #         session.add(LUTDiscordRoles(name=val))
        #     for val in xsldb_lut_season['compte']:
        #         session.add(LUTAccounts(name=val['name']))
        #     for val in xsldb_lut_season['contribution']:
        #         session.add(LUTContribution(name=val['name']))
        #     for val in xsldb_lut_season['connaissance']:
        #         session.add(LUTKnowFrom(name=val['name']))
        #     for val in xsldb_lut_season['type_voie']:
        #         session.add(LUTStreetTypes(name=val['name']))
        #     for val in xsldb_lut_season['saisons']:
        #         session.add(Seasons(name=val['name'],
        #                             start=datetime.fromisoformat(val['start']).date(),
        #                             end=datetime.fromisoformat(val['end']).date()))

        # init member table
        xsldb_lut_member = load_json_file(Path('tests/xlsdb_membre.json'))
        element_list = []
        for val in xsldb_lut_member['membres']:
            new_member = Members()
            element_list.append(new_member)
            if val.get('pseudo_discord'):
                new_member.discord_pseudo=val['pseudo_discord']
            if val.get('prenom') or val.get('nom') or val.get('date_naissance'):
                new_member.credential = Credentials(first_name=val.get('prenom'),
                                                    last_name=val.get('nom'))
                if val.get('date_naissance'):
                    new_member.credential.birthdate = datetime.fromisoformat(val['date_naissance']).date()
            if val.get('emails'):
                principal = True
                for semail in val['emails'].split(';'):
                    new_jct_member_mail = JCTMemberEmail(member=new_member,
                                                         email=Emails(email=semail),
                                                         principal=principal)
                    principal = False
                    element_list.append(new_jct_member_mail)

        async with async_session() as session:
            async with session.begin():
                session.add_all(element_list)

        # async with async_session.begin() as session:
        #     query = sa.select(Users).options(orm.selectinload(Users.emails)).limit(1)
        #     query_result = await session.execute(query)
        #     for qr in query_result.scalars():
        #         print(qr)

        # for AsyncEngine created in function scope, close and
        # clean-up pooled connections
        await db_engine.dispose()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_create_db()))
