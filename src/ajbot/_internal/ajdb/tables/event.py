''' Event db tables
'''
from typing import Optional, TYPE_CHECKING
import functools

import sqlalchemy as sa
from sqlalchemy import orm

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import FormatTypes, get_migrate_mode
from .base import HumanizedDate, SaHumanizedDate, Base, LogMixin
from .season import Season
if TYPE_CHECKING:
    from .member import Member



@functools.total_ordering
class Event(Base, LogMixin):
    """ Event table class
    """
    __tablename__ = 'events'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    date: orm.Mapped[HumanizedDate] = orm.mapped_column(SaHumanizedDate, nullable=False, index=True)
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.id'), nullable=False, index=True)
    season: orm.Mapped['Season'] = orm.relationship(back_populates='events', foreign_keys=season_id, lazy='selectin')
    name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    description: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))

    members: orm.Mapped[list['Member']] = orm.relationship(secondary='JCT_event_member', foreign_keys='[MemberEvent.event_id, MemberEvent.member_id]',
                                                           back_populates='events', lazy='selectin', join_depth=2)
    if get_migrate_mode():
        member_events: orm.Mapped[list['MemberEvent']] = orm.relationship(back_populates='event', foreign_keys='MemberEvent.event_id', lazy='selectin') #AJDB_MIGRATION

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
                return ' - '.join(f"{x}" for x in [self.date, self.name] if x)

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

# many-to-many association tables
#################################

class MemberEvent(Base, LogMixin):
    """ Junction table between events and members
    """
    __tablename__ = 'JCT_event_member'

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    event_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('events.id'), index=True, nullable=False)
    member_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=True, comment='Can be null name/id is lost.')
    presence: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=True, comment='if false: delegated vote')
    comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))

    if get_migrate_mode():
        event: orm.Mapped['Event'] = orm.relationship(back_populates='member_events', foreign_keys=event_id, lazy='selectin') #AJDB_MIGRATION
        member: orm.Mapped['Member'] = orm.relationship(back_populates='event_members', foreign_keys=member_id, lazy='selectin') #AJDB_MIGRATION

    def __str__(self):
        return f"{self.id}, event #{self.event_id}, member #{self.member_id}"


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
