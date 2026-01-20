''' member db table
'''
from typing import Optional, TYPE_CHECKING
import datetime
import functools

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import foreign
from sqlalchemy.ext import associationproxy as ap

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import FormatTypes
from .base import AjMemberId, SaAjMemberId, Base, LogMixin
from .season import Season
from .role import AssoRole, MemberAssoRole
from .membership import Membership
from .event import Event, MemberEvent
if TYPE_CHECKING:
    from .member_private import Credential, MemberEmail, MemberPhone, MemberAddress



@functools.total_ordering
class Member(Base, LogMixin):
    """ Member table class
    """
    __tablename__ = 'members'

    id: orm.Mapped[AjMemberId] = orm.mapped_column(SaAjMemberId, primary_key=True, index=True, unique=True, autoincrement=True)

    credential_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('member_credentials.id'), index=True, nullable=True)
    credential: orm.Mapped[Optional['Credential']] = orm.relationship(back_populates='member', foreign_keys=credential_id, uselist=False, lazy='selectin')

    discord: orm.Mapped[str] = orm.mapped_column(sa.String(50), unique=True, index=True, nullable=True)

    asso_role_member_associations: orm.Mapped[list['MemberAssoRole']] = orm.relationship(back_populates='member', foreign_keys='MemberAssoRole.member_id', lazy='selectin')
    manual_asso_roles: orm.Mapped[list['AssoRole']] = ap.association_proxy('asso_role_member_associations','asso_role',
                                                                           creator=lambda member_obj: MemberAssoRole(member=member_obj),)

    emails: orm.Mapped[list['MemberEmail']] = orm.relationship(back_populates='member', foreign_keys='MemberEmail.member_id', lazy='selectin')
    email_principal: orm.Mapped[Optional['MemberEmail']] = orm.relationship(primaryjoin="and_(Member.id==MemberEmail.member_id,MemberEmail.principal==True)",
                                                                            lazy='selectin',
                                                                            viewonly=True,)
    phones: orm.Mapped[list['MemberPhone']] = orm.relationship(back_populates='member', foreign_keys='MemberPhone.member_id', lazy='selectin')
    phone_principal: orm.Mapped[Optional['MemberPhone']] = orm.relationship(primaryjoin="and_(Member.id==MemberPhone.member_id,MemberPhone.principal==True)",
                                                                            lazy='selectin',
                                                                            viewonly=True,)
    addresses: orm.Mapped[list['MemberAddress']] = orm.relationship(back_populates='member', foreign_keys='MemberAddress.member_id', lazy='selectin')
    address_principal: orm.Mapped[Optional['MemberAddress']] = orm.relationship(primaryjoin="and_(Member.id==MemberAddress.member_id,MemberAddress.principal==True)",
                                                                                lazy='selectin',
                                                                                viewonly=True,)

    memberships: orm.Mapped[list['Membership']] = orm.relationship(back_populates='member', foreign_keys='Membership.member_id', lazy='selectin')
    event_member_associations: orm.Mapped[list['MemberEvent']] = orm.relationship(back_populates='member', foreign_keys='MemberEvent.member_id', lazy='selectin')
    events: ap.AssociationProxy[list['Event']] = ap.association_proxy('event_member_associations','event',
                                                                       creator=lambda member_obj: MemberEvent(member=member_obj),)


    def season_presence_count(self, season_name = None):
        """ return number of related events in provided season. Current if empty
        """
        return len([mbr_evt for mbr_evt in self.events
                    if ((not season_name and mbr_evt.is_in_current_season)
                         or mbr_evt.season.name == season_name)])

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
        mbr_id = f"{self.id:{format_spec}}"
        mbr_creds = f"{self.credential:{format_spec}}" if self.credential else ''
        mbr_disc = ('@' + self.discord) if self.discord else ''
        mbr_email = f"{self.email_principal.email:{format_spec}}" if self.email_principal else ''
        mbr_address = f"{self.address_principal.address:{format_spec}}" if self.address_principal else ''
        mbr_phone = f"{self.phone_principal.phone:{format_spec}}" if self.phone_principal else ''
        mbr_role = f"{self.current_asso_role:{format_spec}}"

        mbr_asso_info = '' if self.is_subscriber else 'non ' #pylint: disable=using-constant-test #variable is not constant
        mbr_asso_info += f"cotisant, {self.season_presence_count()} participation(s) cette saison."

        match format_spec:
            case FormatTypes.RESTRICTED | FormatTypes.FULLSIMPLE:
                return ' - '.join([x for x in [mbr_id, mbr_creds, mbr_disc,] if x])

            case FormatTypes.FULLCOMPLETE:
                return '\n'.join([x for x in [mbr_id, mbr_creds, mbr_disc, mbr_role, mbr_email, mbr_address, mbr_phone,] if x]+[mbr_asso_info])

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

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
