''' Association tables
'''
from typing import Optional, TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from ajbot._internal.exceptions import OtherException
from ajbot._internal.config import get_migrate_mode
from ajbot._internal.ajdb.support import HumanizedDate, SaHumanizedDate, Base
if TYPE_CHECKING:
    from ajbot._internal.ajdb.tables import Member, Email, Phone, PostalAddress, AssoRole, Event


class MemberEmail(Base):
    """ Junction table between members and emails
    """
    __tablename__ = 'JCT_member_email'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship(back_populates='emails', lazy='selectin')
    email_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_emails.id'), index=True, nullable=False)
    email: orm.Mapped['Email'] = orm.relationship(back_populates='members', lazy='selectin')
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
    member: orm.Mapped['Member'] = orm.relationship(back_populates='phones', lazy='selectin')
    phone_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_phones.id'), index=True, nullable=False)
    phone: orm.Mapped['Phone'] = orm.relationship(back_populates='members', lazy='selectin')
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
    member: orm.Mapped['Member'] = orm.relationship(back_populates='addresses', lazy='selectin')
    address_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_addresses.id'), index=True, nullable=False)
    address: orm.Mapped['PostalAddress'] = orm.relationship(back_populates='members', lazy='selectin')
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

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
