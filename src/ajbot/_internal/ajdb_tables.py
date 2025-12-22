''' manage AJ database

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
then manually reformated
'''
from typing import Optional
import datetime
import functools

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import foreign

from thefuzz import fuzz

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import FormatTypes, get_migrate_mode
from ajbot._internal.ajdb_support import HumanizedDate, SaHumanizedDate, AjMemberId, SaAjMemberId, Base


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
    is_current_season: orm.Mapped[bool] = orm.column_property(
                    sa.and_(
                        datetime.datetime.now().date() >= start,
                        sa.or_(end == None,     #pylint: disable=singleton-comparison   #this is SQL syntax
                               datetime.datetime.now().date() <= end)))

    memberships: orm.Mapped[list['Membership']] = orm.relationship('Membership', back_populates='season', lazy='selectin')
    events: orm.Mapped[list['Event']] = orm.relationship('Event', back_populates='season', lazy='selectin')
    # transactions: orm.Mapped[list['Transaction']] = orm.relationship('Transaction', back_populates='seasons')

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        try:
            return ((self.start, self.end) ==
                    (other.start, other.end))
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        try:
            return ((self.start, self.end) <
                    (other.start, other.end))
        except AttributeError:
            return NotImplemented

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
    manual_asso_roles: orm.Mapped[list['AssoRole']] = orm.relationship(secondary='JCT_member_asso_role', back_populates='members', lazy='selectin')

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
    events: orm.Mapped[list['Event']] = orm.relationship(secondary='JCT_event_member', back_populates='members', lazy='selectin')

    if get_migrate_mode():
        event_members: orm.Mapped[list['MemberEvent']] = orm.relationship(back_populates='member', lazy='selectin') #AJDB_MIGRATION
        asso_role_members: orm.Mapped[list['MemberAssoRole']] = orm.relationship(back_populates='member', lazy='selectin') #AJDB_MIGRATION


#     logs: orm.Mapped[list['Log']] = orm.relationship('Log', foreign_keys='[Log.author]', back_populates='members', lazy='selectin')
#     logs_: orm.Mapped[list['Log']] = orm.relationship('Log', foreign_keys='[Log.updated_member]', back_populates='members_', lazy='selectin')

    def season_presence_count(self, season_name = None):
        """ return number of related events in provided season. Current if empty
        """
        return len([mbr_evt for mbr_evt in self.events
                    if ((not season_name and mbr_evt.is_in_current_season)
                         or mbr_evt.season.name == season_name)])

    def current_season_not_subscriber_presence_count(self):
        """ return number of presence if member has not currently subscribed
        """
        if self.is_subscriber:
            return ""
        return self.season_presence_count()

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        try:
            return self.id == other.id
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        try:
            return self.id < other.id
        except AttributeError:
            return NotImplemented

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        mbr_id = self.id
        mbr_creds = self.credential
        mbr_disc = self.discord_pseudo

        match format_spec:
            case FormatTypes.RESTRICTED | FormatTypes.FULLSIMPLE:
                return ' - '.join([f'{x:{format_spec}}' for x in [mbr_id, mbr_creds, mbr_disc,] if x])

            case FormatTypes.FULLCOMPLETE:
                mbr_email = self.email_principal.email if self.email_principal else None
                mbr_address = self.address_principal.address if self.address_principal else None
                mbr_phone = self.phone_principal.phone if self.phone_principal else None
                mbr_role = self.current_asso_role

                mbr_asso_info = '' if self.is_subscriber else 'non ' #pylint: disable=using-constant-test #variable is not constant
                mbr_asso_info += f'cotisant, {self.season_presence_count()} participation(s) cette saison.'
                return '\n'.join([f'{x:{format_spec}}'for x in [mbr_id, mbr_creds, mbr_disc, mbr_role, mbr_email, mbr_address, mbr_phone,] if x]+[mbr_asso_info])

            case _:
                raise AjDbException(f'Le format {format_spec} n\'est pas supporté')


class AssoRole(Base):
    """ Asso role table class
    """
    __tablename__ = 'asso_roles'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True, unique=True,)
    is_member: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False)
    is_past_subscriber: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=True)
    is_subscriber: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=True)
    is_manager: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=True)
    is_owner: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=True)
    discord_roles: orm.Mapped[list['DiscordRole']] = orm.relationship(secondary='JCT_asso_discord_role', back_populates='asso_roles', lazy='selectin')
    members: orm.Mapped[list['Member']] = orm.relationship(secondary='JCT_member_asso_role', back_populates='manual_asso_roles', lazy='selectin')
    if get_migrate_mode():
        member_asso_roles: orm.Mapped[list['MemberAssoRole']] = orm.relationship(back_populates='asso_role', lazy='selectin') #AJDB_MIGRATION

    def __str__(self):
        return f'{self}'

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name


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
    is_in_current_season: orm.Mapped[bool] = orm.column_property(sa.exists().where(
                    sa.and_(
                        Season.id == season_id,
                        Season.is_current_season)))

    statutes_accepted: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)
    has_civil_insurance: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)
    picture_authorized: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)

    know_from_source_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('LUT_know_from_sources.id'), index=True, nullable=True)
    know_from_source: orm.Mapped[Optional['KnowFromSource']] = orm.relationship('KnowFromSource', back_populates='memberships', lazy='selectin')
    contribution_type_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('LUT_contribution_types.id'), index=True, nullable=False)
    contribution_type: orm.Mapped['ContributionType'] = orm.relationship('ContributionType', back_populates='memberships', lazy='selectin')
    # transactions: orm.Mapped[list['Transaction']] = orm.relationship('Transaction', back_populates='memberships')
    # logs: orm.Mapped[list['Log']] = orm.relationship('Log', back_populates='memberships', lazy='selectin')

    #TODO: implement __str__ & __format__

@functools.total_ordering
class Event(Base):
    """ Event table class
    """
    __tablename__ = 'events'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    date: orm.Mapped[HumanizedDate] = orm.mapped_column(SaHumanizedDate, nullable=False, index=True)
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.id'), nullable=False, index=True)
    season: orm.Mapped['Season'] = orm.relationship('Season', back_populates='events', lazy='selectin')
    name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    description: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))

    members: orm.Mapped[list['Member']] = orm.relationship(secondary='JCT_event_member', back_populates='events', lazy='selectin')
    if get_migrate_mode():
        member_events: orm.Mapped[list['MemberEvent']] = orm.relationship(back_populates='event', lazy='selectin') #AJDB_MIGRATION
    # transactions: orm.Mapped[list['Transaction']] = orm.relationship('Transaction', back_populates='events', lazy='selectin')
    # logs: orm.Mapped[list['Log']] = orm.relationship('Log', back_populates='events', lazy='selectin')
    is_in_current_season: orm.Mapped[bool] = orm.column_property(sa.exists().where(
                    sa.and_(
                        Season.id == season_id,
                        Season.is_current_season)))

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        try:
            return self.date == other.date
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        try:
            return self.date < other.date
        except AttributeError:
            return NotImplemented

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

    asso_roles: orm.Mapped[list['AssoRole']] = orm.relationship(secondary='JCT_asso_discord_role', back_populates='discord_roles', lazy='selectin')

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
        try:
            return ((self.last_name.lower(), self.first_name.lower()) ==
                    (other.last_name.lower(), other.first_name.lower()))
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        try:
            return ((self.last_name.lower(), self.first_name.lower()) <
                    (other.last_name.lower(), other.first_name.lower()))
        except AttributeError:
            return NotImplemented

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

    def __str__(self):
        return f'{self.id}, member #{self.member_id}, email #{self.email_id}'


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

    def __str__(self):
        return f'{self.id}, member #{self.member_id}, phone #{self.phone_id}'


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

    def __str__(self):
        return f'{self.id}, member #{self.member_id}, address #{self.address_id}'


class MemberAssoRole(Base):
    """ Junction table between members and asso roles
    """
    __tablename__ = 'JCT_member_asso_role'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    asso_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('asso_roles.id'), index=True, nullable=False)
    start: orm.Mapped[HumanizedDate] = orm.mapped_column(SaHumanizedDate, nullable=False)
    end: orm.Mapped[Optional[HumanizedDate]] = orm.mapped_column(SaHumanizedDate, nullable=True)
    comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)

    if get_migrate_mode():
        asso_role: orm.Mapped['AssoRole'] = orm.relationship(back_populates='member_asso_roles', lazy='selectin') #AJDB_MIGRATION
        member: orm.Mapped['Member'] = orm.relationship(back_populates='asso_role_members', lazy='selectin') #AJDB_MIGRATION


    def __str__(self):
        return f'{self.id}, member #{self.member_id}, asso role #{self.asso_role_id}'


class AssoRoleDiscordRole(Base):
    """ Junction table between Asso and Discord roles
    """
    __tablename__ = 'JCT_asso_discord_role'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    asso_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('asso_roles.id'), index=True, nullable=False)
    discord_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('discord_roles.id'), index=True, nullable=False)

    def __str__(self):
        return f'{self.id}, asso role #{self.asso_role_id}, discord role #{self.discord_role_id}'


class MemberEvent(Base):
    """ Junction table between events and members
    """
    __tablename__ = 'JCT_event_member'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    event_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('events.id'), index=True, nullable=False)
    member_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=True, comment='Can be null name/id is lost.')
    presence: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=True, comment='if false: delegated vote')
    comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))

    if get_migrate_mode():
        event: orm.Mapped['Event'] = orm.relationship(back_populates='member_events', lazy='selectin') #AJDB_MIGRATION
        member: orm.Mapped['Member'] = orm.relationship(back_populates='event_members', lazy='selectin') #AJDB_MIGRATION

    def __str__(self):
        return f'{self.id}, event #{self.event_id}, member #{self.member_id}'


# Member table additional constructs
#########################################

# Build a selectable mapping member -> computed asso_role_id using CASE
_now = datetime.datetime.now().date()

_active_manual_role_cond = sa.and_(
    MemberAssoRole.member_id == Member.id,
    _now >= MemberAssoRole.start,
    sa.or_(MemberAssoRole.end == None, _now <= MemberAssoRole.end),  #pylint: disable=singleton-comparison   #this is SQL syntax
)

_active_manual_role_exists = sa.exists(
    sa.select(1).select_from(MemberAssoRole).where(_active_manual_role_cond)
)

_active_manual_role_select = (
    sa.select(MemberAssoRole.asso_role_id)
    .where(_active_manual_role_cond)
    .limit(1)
    .scalar_subquery()
)

_current_membership_exists = sa.exists(
    sa.select(1)
    .select_from(Membership.__table__.join(Season, Season.id == Membership.season_id))
    .where(
        sa.and_(
            Membership.member_id == Member.id,
            _now >= Season.start,
            sa.or_(Season.end == None, _now <= Season.end),  #pylint: disable=singleton-comparison   #this is SQL syntax
        )
    )
)

_subscriber_role_select = (
    sa.select(AssoRole.id)
    .where(AssoRole.is_subscriber == True) #pylint: disable=singleton-comparison   #this is SQL syntax
    .limit(1)
    .scalar_subquery()
)

_past_membership_exists = sa.exists(
    sa.select(1)
    .select_from(Membership.__table__.join(Season, Season.id == Membership.season_id))
    .where(
        sa.and_(
            Membership.member_id == Member.id,
            Season.end <= _now,
        )
    )
)

_past_subscriber_role_select = (
    sa.select(AssoRole.id)
    .where(AssoRole.is_past_subscriber == True)    #pylint: disable=singleton-comparison   #this is SQL syntax
    .limit(1)
    .scalar_subquery()
)

_default_member_role_select = (
    sa.select(AssoRole.id)
    .where(
        sa.and_(
        AssoRole.is_member == True,                                                               #pylint: disable=singleton-comparison   #this is SQL syntax
            sa.or_(AssoRole.is_subscriber == False, AssoRole.is_subscriber == None),              #pylint: disable=singleton-comparison   #this is SQL syntax
            sa.or_(AssoRole.is_past_subscriber == False, AssoRole.is_past_subscriber == None),    #pylint: disable=singleton-comparison   #this is SQL syntax
            sa.or_(AssoRole.is_manager == False, AssoRole.is_manager == None),                    #pylint: disable=singleton-comparison   #this is SQL syntax
            sa.or_(AssoRole.is_owner == False, AssoRole.is_owner == None),                        #pylint: disable=singleton-comparison   #this is SQL syntax
        )
    )
    .limit(1)
    .scalar_subquery()
)

_current_asso_role_sq = sa.select(
    Member.id.label("member_id"),
    sa.case(
        (_active_manual_role_exists, _active_manual_role_select),
        (_current_membership_exists, _subscriber_role_select),
        (_past_membership_exists, _past_subscriber_role_select),
        else_=_default_member_role_select,
    ).label("asso_role_id"),
).subquery("current_asso_role")

Member.current_asso_role = orm.relationship(
    AssoRole,
    secondary=_current_asso_role_sq,
    primaryjoin=Member.id == foreign(_current_asso_role_sq.c.member_id),
    secondaryjoin=AssoRole.id == foreign(_current_asso_role_sq.c.asso_role_id),
    viewonly=True,
    uselist=False,
    lazy='selectin',
)

Member.is_subscriber = orm.column_property(_current_membership_exists)

Member.is_past_subscriber = orm.column_property(_past_membership_exists)

Member.last_presence = orm.column_property(
    sa.select(sa.func.max(Event.date))
    .select_from(
        Event.__table__.join(
            MemberEvent,
            MemberEvent.event_id == Event.id,
        )
    )
    .where(
        sa.and_(
            MemberEvent.member_id == Member.id,
            MemberEvent.presence == True,             #pylint: disable=singleton-comparison
        )
    )
    .scalar_subquery()
)

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
