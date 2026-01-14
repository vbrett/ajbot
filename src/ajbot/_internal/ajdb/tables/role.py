''' Role (asso & discord) db tables
'''
from typing import Optional, TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm


from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import FormatTypes, get_migrate_mode
from .base import HumanizedDate, SaHumanizedDate, Base, LogMixin
if TYPE_CHECKING:
    from .member import Member



class DiscordRole(Base):
    """ Discord role table class
    """
    __tablename__ = 'discord_roles'

    id: orm.Mapped[int] = orm.mapped_column(sa.BigInteger, primary_key=True, index=True, unique=True,)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, index=True,)

    asso_roles: orm.Mapped[list['AssoRole']] = orm.relationship(secondary='JCT_asso_discord_role', foreign_keys='[AssoRoleDiscordRole.asso_role_id, AssoRoleDiscordRole.discord_role_id]',
                                                                back_populates='discord_roles', lazy='selectin')

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.FULLCOMPLETE | FormatTypes.FULLSIMPLE | FormatTypes.RESTRICTED:
                return self.name

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")


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
    discord_roles: orm.Mapped[list['DiscordRole']] = orm.relationship(secondary='JCT_asso_discord_role', foreign_keys='[AssoRoleDiscordRole.asso_role_id, AssoRoleDiscordRole.discord_role_id]',
                                                                      back_populates='asso_roles', lazy='selectin', join_depth=2)
    members: orm.Mapped[list['Member']] = orm.relationship(secondary='JCT_member_asso_role', foreign_keys='[MemberAssoRole.asso_role_id, MemberAssoRole.member_id]',
                                                           back_populates='manual_asso_roles', lazy='selectin', join_depth=2)
    if get_migrate_mode():
        member_asso_roles: orm.Mapped[list['MemberAssoRole']] = orm.relationship(back_populates='asso_role', foreign_keys='MemberAssoRole.asso_role_id', lazy='selectin') #AJDB_MIGRATION

    def __str__(self):
        return f"{self}"

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name


# many-to-many association tables
#################################

class AssoRoleDiscordRole(Base):
    """ Junction table between Asso and Discord roles
    """
    __tablename__ = 'JCT_asso_discord_role'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    asso_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('asso_roles.id'), index=True, nullable=False)
    discord_role_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('discord_roles.id'), index=True, nullable=False)

    def __str__(self):
        return f"{self.id}, asso role #{self.asso_role_id}, discord role #{self.discord_role_id}"

class MemberAssoRole(Base, LogMixin):
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
        asso_role: orm.Mapped['AssoRole'] = orm.relationship(back_populates='member_asso_roles', foreign_keys=asso_role_id, lazy='selectin') #AJDB_MIGRATION
        member: orm.Mapped['Member'] = orm.relationship(back_populates='asso_role_members', foreign_keys=member_id, lazy='selectin') #AJDB_MIGRATION


    def __str__(self):
        return f"{self.id}, member #{self.member_id}, asso role #{self.asso_role_id}"

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
