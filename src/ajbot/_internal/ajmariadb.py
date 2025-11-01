""" test deployment of a MariaDB instance

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
"""
import sys
import asyncio
from typing import List
from typing import Optional
from datetime import datetime, date #, time

import sqlalchemy as sa
from sqlalchemy.ext import asyncio as aio_sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
# from sqlalchemy.orm import selectinload

from ajbot._internal.config import AjConfig


class Base(aio_sa.AsyncAttrs, DeclarativeBase):
    """ Base ORM class
    """


# Enumeration tables
################################
class EnumAccounts(Base):
    """ List of supported transaction accounts
    """
    __tablename__ = 'enum_accounts'
    name: Mapped[str] = mapped_column(sa.String(20), primary_key=True, unique=True, index=True)
    transaction: Mapped[List['Transaction']] = relationship('Transaction', back_populates='enum_accounts')

class EnumContribution(Base):
    """ List of supported contribution levels
    """
    __tablename__ = 'enum_contribution'
    name: Mapped[str] = mapped_column(sa.String(20), primary_key=True, unique=True, index=True)
    memberships: Mapped[List['Memberships']] = relationship('Memberships', back_populates='enum_contribution')

class EnumDiscordRoles(Base):
    """ List of supported Discord roles
    """
    __tablename__ = 'enum_discord_roles'
    name: Mapped[str] = mapped_column(sa.String(20), primary_key=True, unique=True, index=True)
    members: Mapped[List['Members']] = relationship('Members', back_populates='enum_discord_roles')

class EnumKnowFrom(Base):
    """ List of supported sources of knowing about the association
    """
    __tablename__ = 'enum_know_from'
    name: Mapped[str] = mapped_column(sa.String(50), primary_key=True, unique=True, index=True)

    memberships: Mapped[List['Memberships']] = relationship('Memberships', back_populates='enum_know_from')

class EnumLogCategories(Base):
    """ List of supported log categories
    """
    __tablename__ = 'enum_log_categories'
    name: Mapped[str] = mapped_column(sa.String(20), primary_key=True, unique=True, index=True)
    log: Mapped[List['Log']] = relationship('Log', back_populates='enum_log_categories')

class EnumStreetTypes(Base):
    """ List of supported street types
    """
    __tablename__ = 'enum_street_types'
    name: Mapped[str] = mapped_column(sa.String(20), primary_key=True, unique=True, index=True)
    addresses: Mapped[List['Addresses']] = relationship('Addresses', back_populates='enum_street_types')



# Members private data tables & relations
#########################################

class Emails(Base):
    """ user email table class
    """
    __tablename__ = 'emails'
    email: Mapped[str] = mapped_column(sa.String(50), primary_key=True, unique=True, index=True)

class Phones(Base):
    """ user phone number table class
    """
    __tablename__ = 'phones'
    phone_number: Mapped[str] = mapped_column(sa.String(20), primary_key=True, unique=True, index=True)

class Addresses(Base):
    """ user address table class
    """
    __tablename__ = 'addresses'
    address_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    street_type: Mapped[str] = mapped_column(sa.String(20))
    street_num: Mapped[Optional[str]] = mapped_column(sa.String(20))
    street_extra: Mapped[Optional[str]] = mapped_column(sa.String(255))
    street_name: Mapped[Optional[str]] = mapped_column(sa.String(255))
    zip_code: Mapped[Optional[int]] = mapped_column(sa.Integer)
    town: Mapped[Optional[str]] = mapped_column(sa.String(255))
    other: Mapped[Optional[str]] = mapped_column(sa.String(255))

    enum_street_types: Mapped['EnumStreetTypes'] = relationship('EnumStreetTypes', back_populates='addresses')

class Identities(Base):
    """ user identity table class
    """
    __tablename__ = 'identities'
    member_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    first_name: Mapped[str] = mapped_column(sa.String(50), primary_key=True)
    last_name: Mapped[str] = mapped_column(sa.String(50), primary_key=True)

    member: Mapped['Members'] = relationship('Members', back_populates='identities')

t_event_member_xref = sa.Table(
    'event_member_xref', Base.metadata,
    sa.Column('event', sa.String(50), nullable=False),
    sa.Column('member', sa.Integer, nullable=False),
    sa.ForeignKeyConstraint(['event'], ['events.name'], name='FK_events_TO_event_member_xref'),
    sa.ForeignKeyConstraint(['member'], ['members.member_id'], name='FK_members_TO_event_member_xref'),
    sa.Index('FK_events_TO_event_member_xref', 'event'),
    sa.Index('FK_members_TO_event_member_xref', 'member')
)

t_member_address_xref = sa.Table(
    'member_address_xref', Base.metadata,
    sa.Column('member_id', sa.Integer, nullable=False),
    sa.Column('address_id', sa.Integer, nullable=False),
    sa.Column('principal', sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence'),
    sa.ForeignKeyConstraint(['address_id'], ['addresses.address_id'], name='FK_addresses_TO_member_address_xref'),
    sa.ForeignKeyConstraint(['member_id'], ['members.member_id'], name='FK_members_TO_member_address_xref'),
    sa.Index('FK_addresses_TO_member_address_xref', 'address_id'),
    sa.Index('FK_members_TO_member_address_xref', 'member_id'),
    comment='RGPD info'
)

t_member_email_xref = sa.Table(
    'member_email_xref', Base.metadata,
    sa.Column('member_id', sa.Integer, nullable=False),
    sa.Column('email', sa.String(50), nullable=False),
    sa.Column('principal', sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence'),
    sa.ForeignKeyConstraint(['email'], ['emails.email'], name='FK_emails_TO_member_email_xref'),
    sa.ForeignKeyConstraint(['member_id'], ['members.member_id'], name='FK_members_TO_member_email_xref'),
    sa.Index('FK_emails_TO_member_email_xref', 'email'),
    sa.Index('FK_members_TO_member_email_xref', 'member_id'),
    comment='RGPD info'
)

t_member_phone_xref = sa.Table(
    'member_phone_xref', Base.metadata,
    sa.Column('member_id', sa.Integer, nullable=False),
    sa.Column('phone_number', sa.String(20), nullable=False),
    sa.Column('principal', sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence'),
    sa.ForeignKeyConstraint(['member_id'], ['members.member_id'], name='FK_members_TO_member_phone_xref'),
    sa.ForeignKeyConstraint(['phone_number'], ['phones.phone_number'], name='FK_phones_TO_member_phone_xref'),
    sa.Index('FK_members_TO_member_phone_xref', 'member_id'),
    sa.Index('FK_phones_TO_member_phone_xref', 'phone_number'),
    comment='RGPD info'
)


# Member table
################################
class Members(Base):
    """ Member table class
    """
    __tablename__ = 'members'
    member_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    discord_role: Mapped[str] = mapped_column(sa.String(20), nullable=False, comment='to override role defined by membership rules')
    discord_pseudo: Mapped[Optional[str]] = mapped_column(sa.String(50))
    comment: Mapped[Optional[str]] = mapped_column(sa.String(255))

    events: Mapped[List['Events']] = relationship('Events', secondary='event_member_xref', back_populates='members')
    enum_discord_roles: Mapped['EnumDiscordRoles'] = relationship('EnumDiscordRoles', back_populates='members')
    identities: Mapped[List['Identities']] = relationship('Identities', back_populates='member')
    memberships: Mapped[List['Memberships']] = relationship('Memberships', back_populates='member')
    log: Mapped[List['Log']] = relationship('Log', foreign_keys='[Log.author]', back_populates='members')
    log_: Mapped[List['Log']] = relationship('Log', foreign_keys='[Log.member]', back_populates='members_')



class Assets(Base):
    """ Association assets table class
    """
    __tablename__ = 'assets'
    asset_id: Mapped[int] = mapped_column(primary_key=True, index=True, unique=True)
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    transaction: Mapped[List['Transaction']] = relationship('Transaction', back_populates='assets')

class Events(Base):
    """ Events table class
    """
    __tablename__ = 'events'

    name: Mapped[str] = mapped_column(sa.String(50), primary_key=True, index=True, unique=True)
    special: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    description: Mapped[Optional[str]] = mapped_column(sa.String(255))

    members: Mapped[List['Members']] = relationship('Members', secondary='event_member_xref', back_populates='events')
    transaction: Mapped[List['Transaction']] = relationship('Transaction', back_populates='events')
    log: Mapped[List['Log']] = relationship('Log', back_populates='events')



class Seasons(Base):
    """ Seasons table class
    """
    __tablename__ = 'seasons'
    season: Mapped[str] = mapped_column(sa.String(10), primary_key=True, index=True, unique=True)
    start: Mapped[date] = mapped_column(sa.Date, nullable=False)
    end: Mapped[date] = mapped_column(sa.Date, nullable=False)

    log: Mapped[List['Log']] = relationship('Log', back_populates='seasons')


class Memberships(Base):
    """ Memberships table class
    """
    __tablename__ = 'memberships'
    membership_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    contribution: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    picture_authorized: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    statutes_accepted: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    civil_insurance: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    know_from: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    enum_contribution: Mapped['EnumContribution'] = relationship('EnumContribution', back_populates='memberships')
    enum_know_from: Mapped['EnumKnowFrom'] = relationship('EnumKnowFrom', back_populates='memberships')
    member: Mapped['Members'] = relationship('Members', back_populates='memberships')
    transaction: Mapped[List['Transaction']] = relationship('Transaction', back_populates='memberships')
    log: Mapped[List['Log']] = relationship('Log', back_populates='memberships')


class Transaction(Base):
    """ Transaction table class
    """
    __tablename__ = 'transaction'
    transaction_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    event: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    account: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(sa.String(20))
    asset: Mapped[Optional[int]] = mapped_column(sa.Integer)
    membership: Mapped[Optional[int]] = mapped_column(sa.Integer)
    credit: Mapped[Optional[float]] = mapped_column(sa.Float)
    debit: Mapped[Optional[float]] = mapped_column(sa.Float)
    comment: Mapped[Optional[str]] = mapped_column(sa.String(100))

    enum_accounts: Mapped['EnumAccounts'] = relationship('EnumAccounts', back_populates='transaction')
    assets: Mapped[Optional['Assets']] = relationship('Assets', back_populates='transaction')
    events: Mapped['Events'] = relationship('Events', back_populates='transaction')
    memberships: Mapped[Optional['Memberships']] = relationship('Memberships', back_populates='transaction')
    log: Mapped[List['Log']] = relationship('Log', back_populates='transaction_')


class Log(Base):
    """ Log table class
    """
    __tablename__ = 'log'
    log_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(sa.DateTime, nullable=False)
    author: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    season: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    category: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(sa.String(50))
    detail: Mapped[Optional[str]] = mapped_column(sa.String(100))
    comment: Mapped[Optional[str]] = mapped_column(sa.String(255))
    event: Mapped[Optional[str]] = mapped_column(sa.String(50))
    membership: Mapped[Optional[int]] = mapped_column(sa.Integer)
    member: Mapped[Optional[int]] = mapped_column(sa.Integer)
    transaction: Mapped[Optional[int]] = mapped_column(sa.Integer)

    members: Mapped['Members'] = relationship('Members', foreign_keys=[author], back_populates='log')
    enum_log_categories: Mapped['EnumLogCategories'] = relationship('EnumLogCategories', back_populates='log')
    events: Mapped[Optional['Events']] = relationship('Events', back_populates='log')
    members_: Mapped[Optional['Members']] = relationship('Members', foreign_keys=[member], back_populates='log_')
    memberships: Mapped[Optional['Memberships']] = relationship('Memberships', back_populates='log')
    seasons: Mapped['Seasons'] = relationship('Seasons', back_populates='log')
    transaction_: Mapped[Optional['Transaction']] = relationship('Transaction', back_populates='log')




async def _main():
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
        # async_session = aio_sa.async_sessionmaker(bind = db_engine, expire_on_commit=False)

        async with db_engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        # new_user = Users(first_name="Machin", emails=[Emails(email="toto@here.com")])

        # async with async_session.begin() as session:
        #     session.add(new_user)

        # async with async_session.begin() as session:
        #     query = sa.select(Users).options(selectinload(Users.emails)).limit(1)
        #     query_result = await session.execute(query)
        #     for qr in query_result.scalars():
        #         print(qr)

        # # for AsyncEngine created in function scope, close and
        # # clean-up pooled connections
        # await db_engine.dispose()

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
