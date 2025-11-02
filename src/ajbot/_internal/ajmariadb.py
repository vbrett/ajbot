""" test deployment of a MariaDB instance

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
"""
import sys
import asyncio
from typing import List
from typing import Optional
from datetime import datetime, date #, time
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext import asyncio as aio_sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
# from sqlalchemy.orm import selectinload

from vbrpytools.dicjsontools import load_json_file

from ajbot._internal.config import AjConfig


class Base(aio_sa.AsyncAttrs, DeclarativeBase):
    """ Base ORM class
    """


# Lookup tables
################################
class LUTAccounts(Base):
    """ List of supported transaction accounts
    """
    __tablename__ = 'LUT_accounts'
    __table_args__ = (
        sa.Index('UQ_id', 'id', unique=True),
        sa.Index('UQ_name', 'name', unique=True)
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    transaction: Mapped[List['Transaction']] = relationship('Transaction', back_populates='LUT_accounts')


class LUTContribution(Base):
    """ List of supported contribution levels
    """
    __tablename__ = 'LUT_contribution'
    __table_args__ = (
        sa.Index('UQ_id', 'id', unique=True),
        sa.Index('UQ_name', 'name', unique=True),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    memberships: Mapped[List['Memberships']] = relationship('Memberships', back_populates='LUT_contribution')


class LUTDiscordRoles(Base):
    """ List of supported Discord roles
    """
    __tablename__ = 'LUT_discord_roles'
    __table_args__ = (
        sa.Index('UQ_id', 'id', unique=True),
        sa.Index('UQ_name', 'name', unique=True)
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    members: Mapped[List['Members']] = relationship('Members', back_populates='LUT_discord_roles')


class LUTKnowFrom(Base):
    """ List of supported sources of knowing about the association
    """
    __tablename__ = 'LUT_know_from'
    __table_args__ = (
        sa.Index('UQ_id', 'id', unique=True),
        sa.Index('UQ_name', 'name', unique=True)
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    memberships: Mapped[List['Memberships']] = relationship('Memberships', back_populates='LUT_know_from')


class LUTStreetTypes(Base):
    """ List of supported street types
    """
    __tablename__ = 'LUT_street_types'
    __table_args__ = (
        sa.Index('UQ_id', 'id', unique=True),
        sa.Index('UQ_name', 'name', unique=True)
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    addresses: Mapped[List['Addresses']] = relationship('Addresses', back_populates='LUT_street_types')


# Main tables
################################


class Assets(Base):
    """ Assets table class
    """
    __tablename__ = 'assets'
    __table_args__ = (
        sa.Index('UQ_asset_id', 'asset_id', unique=True),
    )

    asset_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.String(255))

    transaction: Mapped[List['Transaction']] = relationship('Transaction', back_populates='assets')


class Seasons(Base):
    """ Seasons table class
    """
    __tablename__ = 'seasons'
    __table_args__ = (
        sa.Index('UQ_end', 'end', unique=True),
        sa.Index('UQ_name', 'name', unique=True),
        sa.Index('UQ_season_id', 'season_id', unique=True),
        sa.Index('UQ_start', 'start', unique=True)
    )

    season_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    name: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    start: Mapped[date] = mapped_column(sa.Date, nullable=False)
    end: Mapped[date] = mapped_column(sa.Date, nullable=False)

    events: Mapped[List['Events']] = relationship('Events', back_populates='seasons')
    memberships: Mapped[List['Memberships']] = relationship('Memberships', back_populates='seasons')
    transaction: Mapped[List['Transaction']] = relationship('Transaction', back_populates='seasons')


class Events(Base):
    """ Events table class
    """
    __tablename__ = 'events'
    __table_args__ = (
        sa.ForeignKeyConstraint(['season'], ['seasons.season_id'], name='FK_seasons_TO_events'),
        sa.Index('FK_seasons_TO_events', 'season'),
        sa.Index('UQ_date', 'event_date', unique=True),
        sa.Index('UQ_event_id', 'event_id', unique=True)
    )

    event_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    event_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    season: Mapped[int] = mapped_column(sa.Integer, nullable=False, comment='shall be computed based on event_date')
    name: Mapped[Optional[str]] = mapped_column(sa.String(50))
    description: Mapped[Optional[str]] = mapped_column(sa.String(255))

    seasons: Mapped['Seasons'] = relationship('Seasons', back_populates='events')
    JCT_event_member: Mapped[List['JCTEventMember']] = relationship('JCTEventMember', back_populates='events')
    transaction: Mapped[List['Transaction']] = relationship('Transaction', back_populates='events')
    log: Mapped[List['Log']] = relationship('Log', back_populates='events')


class Members(Base):
    """ Member table class
    """
    __tablename__ = 'members'
    __table_args__ = (
        sa.ForeignKeyConstraint(['discord_role'], ['LUT_discord_roles.id'], name='FK_LUT_discord_roles_TO_members'),
        sa.Index('FK_LUT_discord_roles_TO_members', 'discord_role'),
        sa.Index('UQ_member_id', 'member_id', unique=True)
    )

    member_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    discord_role: Mapped[int] = mapped_column(sa.Integer, nullable=False, comment='to override role defined by membership rules')
    discord_pseudo: Mapped[Optional[str]] = mapped_column(sa.String(50))
    comment: Mapped[Optional[str]] = mapped_column(sa.String(255))

    LUT_discord_roles: Mapped['LUTDiscordRoles'] = relationship('LUTDiscordRoles', back_populates='members')
    JCT_event_member: Mapped[List['JCTEventMember']] = relationship('JCTEventMember', back_populates='members')
    JCT_member_address: Mapped[List['JCTMemberAddress']] = relationship('JCTMemberAddress', back_populates='member')
    JCT_member_email: Mapped[List['JCTMemberEmail']] = relationship('JCTMemberEmail', back_populates='member')
    JCT_member_phone: Mapped[List['JCTMemberPhone']] = relationship('JCTMemberPhone', back_populates='member')
    memberships: Mapped[List['Memberships']] = relationship('Memberships', back_populates='member')
    log: Mapped[List['Log']] = relationship('Log', foreign_keys='[Log.author]', back_populates='members')
    log_: Mapped[List['Log']] = relationship('Log', foreign_keys='[Log.updated_member]', back_populates='members_')


class Memberships(Base):
    """ Memberships table class
    """
    __tablename__ = 'memberships'
    __table_args__ = (
        sa.ForeignKeyConstraint(['contribution'], ['LUT_contribution.id'], name='FK_LUT_contribution_TO_memberships'),
        sa.ForeignKeyConstraint(['know_from'], ['LUT_know_from.id'], name='FK_LUT_know_from_TO_memberships'),
        sa.ForeignKeyConstraint(['member_id'], ['members.member_id'], name='FK_members_TO_memberships'),
        sa.ForeignKeyConstraint(['season'], ['seasons.season_id'], name='FK_seasons_TO_memberships'),
        sa.Index('FK_LUT_contribution_TO_memberships', 'contribution'),
        sa.Index('FK_LUT_know_from_TO_memberships', 'know_from'),
        sa.Index('FK_members_TO_memberships', 'member_id'),
        sa.Index('FK_seasons_TO_memberships', 'season'),
        sa.Index('UQ_membership_id', 'membership_id', unique=True),
        {'comment': 'each association shall be unique - CONSTRAINT IX_Intersection '
                'UNIQUE(Table A, Table B )'}
    )

    membership_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    membership_date: Mapped[date] = mapped_column(sa.Date, nullable=False, comment='coupling between this and season')
    season: Mapped[int] = mapped_column(sa.Integer, nullable=False, comment='[season;member_id] is unique')
    member_id: Mapped[int] = mapped_column(sa.Integer, nullable=False, comment='[season;member_id] is unique')
    contribution: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    picture_authorized: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    statutes_accepted: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    civil_insurance: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    know_from: Mapped[Optional[int]] = mapped_column(sa.Integer)

    LUT_contribution: Mapped['LUTContribution'] = relationship('LUTContribution', back_populates='memberships')
    LUT_know_from: Mapped[Optional['LUTKnowFrom']] = relationship('LUTKnowFrom', back_populates='memberships')
    member: Mapped['Members'] = relationship('Members', back_populates='memberships')
    seasons: Mapped['Seasons'] = relationship('Seasons', back_populates='memberships')
    transaction: Mapped[List['Transaction']] = relationship('Transaction', back_populates='memberships')
    log: Mapped[List['Log']] = relationship('Log', back_populates='memberships')


class Transaction(Base):
    """ Transaction table class
    """
    __tablename__ = 'transaction'
    __table_args__ = (
        sa.ForeignKeyConstraint(['account'], ['LUT_accounts.id'], name='FK_LUT_accounts_TO_transaction'),
        sa.ForeignKeyConstraint(['associated_asset'], ['assets.asset_id'], name='FK_assets_TO_transaction'),
        sa.ForeignKeyConstraint(['associated_event'], ['events.event_id'], name='FK_events_TO_transaction'),
        sa.ForeignKeyConstraint(['associated_membership'], ['memberships.membership_id'], name='FK_memberships_TO_transaction'),
        sa.ForeignKeyConstraint(['season'], ['seasons.season_id'], name='FK_seasons_TO_transaction'),
        sa.Index('FK_LUT_accounts_TO_transaction', 'account'),
        sa.Index('FK_assets_TO_transaction', 'associated_asset'),
        sa.Index('FK_events_TO_transaction', 'associated_event'),
        sa.Index('FK_memberships_TO_transaction', 'associated_membership'),
        sa.Index('FK_seasons_TO_transaction', 'season'),
        sa.Index('UQ_transaction_id', 'transaction_id', unique=True)
    )

    transaction_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    transaction_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    season: Mapped[int] = mapped_column(sa.Integer, nullable=False, comment='shall be computed based on transaction_date')
    account: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    associated_event: Mapped[Optional[int]] = mapped_column(sa.Integer)
    associated_asset: Mapped[Optional[int]] = mapped_column(sa.Integer)
    associated_membership: Mapped[Optional[int]] = mapped_column(sa.Integer)
    title: Mapped[Optional[str]] = mapped_column(sa.String(50), comment='non empty only if all associated_xxx are empty')
    details: Mapped[Optional[str]] = mapped_column(sa.String(100))
    credit: Mapped[Optional[float]] = mapped_column(sa.Float)
    debit: Mapped[Optional[float]] = mapped_column(sa.Float)
    comment: Mapped[Optional[str]] = mapped_column(sa.String(100))

    LUT_accounts: Mapped['LUTAccounts'] = relationship('LUTAccounts', back_populates='transaction')
    assets: Mapped[Optional['Assets']] = relationship('Assets', back_populates='transaction')
    events: Mapped[Optional['Events']] = relationship('Events', back_populates='transaction')
    memberships: Mapped[Optional['Memberships']] = relationship('Memberships', back_populates='transaction')
    seasons: Mapped['Seasons'] = relationship('Seasons', back_populates='transaction')
    log: Mapped[List['Log']] = relationship('Log', back_populates='transaction')


class Log(Base):
    """ Log table class
    """
    __tablename__ = 'log'
    __table_args__ = (
        sa.ForeignKeyConstraint(['author'], ['members.member_id'], name='FK_members_TO_log1'),
        sa.ForeignKeyConstraint(['updated_event'], ['events.event_id'], name='FK_events_TO_log'),
        sa.ForeignKeyConstraint(['updated_member'], ['members.member_id'], name='FK_members_TO_log'),
        sa.ForeignKeyConstraint(['updated_membership'], ['memberships.membership_id'], name='FK_memberships_TO_log'),
        sa.ForeignKeyConstraint(['updated_transaction'], ['transaction.transaction_id'], name='FK_transaction_TO_log'),
        sa.Index('FK_events_TO_log', 'updated_event'),
        sa.Index('FK_members_TO_log', 'updated_member'),
        sa.Index('FK_members_TO_log1', 'author'),
        sa.Index('FK_memberships_TO_log', 'updated_membership'),
        sa.Index('FK_transaction_TO_log', 'updated_transaction'),
        sa.Index('UQ_datetime', 'log_datetime', unique=True)
    )

    log_datetime: Mapped[datetime] = mapped_column(sa.DateTime, primary_key=True)
    author: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(sa.String(50))
    comment: Mapped[Optional[str]] = mapped_column(sa.String(255))
    updated_event: Mapped[Optional[int]] = mapped_column(sa.Integer)
    updated_membership: Mapped[Optional[int]] = mapped_column(sa.Integer)
    updated_member: Mapped[Optional[int]] = mapped_column(sa.Integer)
    updated_transaction: Mapped[Optional[int]] = mapped_column(sa.Integer)

    members: Mapped['Members'] = relationship('Members', foreign_keys=[author], back_populates='log')
    events: Mapped[Optional['Events']] = relationship('Events', back_populates='log')
    members_: Mapped[Optional['Members']] = relationship('Members', foreign_keys=[updated_member], back_populates='log_')
    memberships: Mapped[Optional['Memberships']] = relationship('Memberships', back_populates='log')
    transaction: Mapped[Optional['Transaction']] = relationship('Transaction', back_populates='log')



# Members private data tables
#########################################


class Emails(Base):
    """ user email table class
    """
    __tablename__ = 'emails'
    __table_args__ = (
        sa.Index('UQ_email', 'email', unique=True),
        sa.Index('UQ_email_id', 'email_id', unique=True),
        {'comment': 'contain RGPD info'}
    )

    email_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    email: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    JCT_member_email: Mapped[List['JCTMemberEmail']] = relationship('JCTMemberEmail', back_populates='email')


class Phones(Base):
    """ user phone number table class
    """
    __tablename__ = 'phones'
    __table_args__ = (
        sa.Index('UQ_phone_id', 'phone_id', unique=True),
        sa.Index('UQ_phone_number', 'phone_number', unique=True),
        {'comment': 'contain RGPD info'}
    )

    phone_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    phone_number: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    JCT_member_phone: Mapped[List['JCTMemberPhone']] = relationship('JCTMemberPhone', back_populates='phone')


class Addresses(Base):
    """ user address table class
    """
    __tablename__ = 'addresses'
    __table_args__ = (
        sa.ForeignKeyConstraint(['street_type'], ['LUT_street_types.id'], name='FK_LUT_street_types_TO_addresses'),
        sa.Index('FK_LUT_street_types_TO_addresses', 'street_type'),
        sa.Index('UQ_address_id', 'address_id', unique=True),
        {'comment': 'contain RGPD info'}
    )

    address_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    street_num: Mapped[Optional[str]] = mapped_column(sa.String(50))
    street_type: Mapped[Optional[int]] = mapped_column(sa.Integer)
    street_extra: Mapped[Optional[str]] = mapped_column(sa.String(255))
    street_name: Mapped[Optional[str]] = mapped_column(sa.String(255))
    zip_code: Mapped[Optional[int]] = mapped_column(sa.Integer)
    town: Mapped[Optional[str]] = mapped_column(sa.String(255))
    other: Mapped[Optional[str]] = mapped_column(sa.String(255))

    LUT_street_types: Mapped[Optional['LUTStreetTypes']] = relationship('LUTStreetTypes', back_populates='addresses')
    JCT_member_address: Mapped[List['JCTMemberAddress']] = relationship('JCTMemberAddress', back_populates='address')


class Credentials(Members):
    """ user credentials table class
    """
    __tablename__ = 'credentials'
    __table_args__ = (
        sa.ForeignKeyConstraint(['member_id'], ['members.member_id'], name='FK_members_TO_credentials'),
        sa.Index('UQ_member_id', 'member_id', unique=True),
        {'comment': 'contain RGPD info'}
    )

    member_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    first_name: Mapped[Optional[str]] = mapped_column(sa.String(50))
    last_name: Mapped[Optional[str]] = mapped_column(sa.String(50))
    birthdate: Mapped[Optional[date]] = mapped_column(sa.Date)


# Junction tables
#########################################


class JCTEventMember(Base):
    """ Junction table between events and members
    """
    __tablename__ = 'JCT_event_member'
    __table_args__ = (
        sa.ForeignKeyConstraint(['event'], ['events.event_id'], name='FK_events_TO_JCT_event_member'),
        sa.ForeignKeyConstraint(['member'], ['members.member_id'], name='FK_members_TO_JCT_event_member'),
        sa.Index('FK_events_TO_JCT_event_member', 'event'),
        sa.Index('FK_members_TO_JCT_event_member', 'member'),
        sa.Index('UQ_id', 'id', unique=True)
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    event: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    presence: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True, comment='if false: delegating vote')
    member: Mapped[Optional[int]] = mapped_column(sa.Integer, comment='Can be null name/id is lost.')
    comment: Mapped[Optional[str]] = mapped_column(sa.String(100))

    events: Mapped['Events'] = relationship('Events', back_populates='JCT_event_member')
    members: Mapped[Optional['Members']] = relationship('Members', back_populates='JCT_event_member')


class JCTMemberAddress(Base):
    """ Junction table between members and addresses
    """
    __tablename__ = 'JCT_member_address'
    __table_args__ = (
        sa.ForeignKeyConstraint(['address_id'], ['addresses.address_id'], name='FK_addresses_TO_JCT_member_address'),
        sa.ForeignKeyConstraint(['member_id'], ['members.member_id'], name='FK_members_TO_JCT_member_address'),
        sa.Index('FK_addresses_TO_JCT_member_address', 'address_id'),
        sa.Index('FK_members_TO_JCT_member_address', 'member_id'),
        sa.Index('UQ_id', 'id', unique=True),
        {'comment': 'contain RGPD info'}
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    member_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    address_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    principal: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')

    address: Mapped['Addresses'] = relationship('Addresses', back_populates='JCT_member_address')
    member: Mapped['Members'] = relationship('Members', back_populates='JCT_member_address')


class JCTMemberEmail(Base):
    """ Junction table between members and emails
    """
    __tablename__ = 'JCT_member_email'
    __table_args__ = (
        sa.ForeignKeyConstraint(['email_id'], ['emails.email_id'], name='FK_emails_TO_JCT_member_email'),
        sa.ForeignKeyConstraint(['member_id'], ['members.member_id'], name='FK_members_TO_JCT_member_email'),
        sa.Index('FK_emails_TO_JCT_member_email', 'email_id'),
        sa.Index('FK_members_TO_JCT_member_email', 'member_id'),
        sa.Index('UQ_id', 'id', unique=True),
        {'comment': 'contain RGPD info'}
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    member_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    email_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    principal: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')

    email: Mapped['Emails'] = relationship('Emails', back_populates='JCT_member_email')
    member: Mapped['Members'] = relationship('Members', back_populates='JCT_member_email')


class JCTMemberPhone(Base):
    """ Junction table between members and phones
    """
    __tablename__ = 'JCT_member_phone'
    __table_args__ = (
        sa.ForeignKeyConstraint(['member_id'], ['members.member_id'], name='FK_members_TO_JCT_member_phone'),
        sa.ForeignKeyConstraint(['phone_id'], ['phones.phone_id'], name='FK_phones_TO_JCT_member_phone'),
        sa.Index('FK_members_TO_JCT_member_phone', 'member_id'),
        sa.Index('FK_phones_TO_JCT_member_phone', 'phone_id'),
        sa.Index('UQ_id', 'id', unique=True),
        {'comment': 'contain RGPD info'}
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, comment='UUID')
    member_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    phone_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    principal: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')

    member: Mapped['Members'] = relationship('Members', back_populates='JCT_member_phone')
    phone: Mapped['Phones'] = relationship('Phones', back_populates='JCT_member_phone')






async def _create_db():
    """ main function
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

        async with db_engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        xsldb_lut_season = load_json_file(Path('tests/xlsdb_LUP_saison.json'))

        # init lookup tables
        async with async_session.begin() as session:
            for val in ['Membre','Membre saison préc','Artisan',
                        'Bureau - Communication', 'Bureau - Président','Bureau - Secrétaire',
                        'Bureau - Trésorier','Bureau - Autre', 'Bureau - Admin',
                        'ProBot ✨','Simple Poll','VbrBot']:
                session.add(LUTDiscordRoles(name=val))
            for val in xsldb_lut_season['compte']: #['Espèce', 'Chèque', 'Banque', 'helloAsso']:
                session.add(LUTAccounts(name=val['name']))
            for val in xsldb_lut_season['contribution']: #['plein', 'réduit', 'offert', 'autre', 'inconnu']:
                session.add(LUTContribution(name=val['name']))
            for val in xsldb_lut_season['connaissance']: #['Forum Asso','Gobelin / Dédale / Afterwork','Bouche à oreille','Réseaux sociaux','Autre']:
                session.add(LUTKnowFrom(name=val['name']))
            for val in xsldb_lut_season['type_voie']: #['avenue','rue','boulevard','place','allée','impasse','passage','sente','chemin']:
                session.add(LUTStreetTypes(name=val['name']))
            for val in xsldb_lut_season['saisons']:
                session.add(Seasons(name=val['name'],
                                    start=datetime.fromisoformat(val['start']).date(),
                                    end=datetime.fromisoformat(val['end']).date()))


        # async with async_session.begin() as session:
        #     query = sa.select(Users).options(selectinload(Users.emails)).limit(1)
        #     query_result = await session.execute(query)
        #     for qr in query_result.scalars():
        #         print(qr)

        # for AsyncEngine created in function scope, close and
        # clean-up pooled connections
        await db_engine.dispose()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_create_db()))
