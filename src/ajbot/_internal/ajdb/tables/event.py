''' Event db tables
'''
from typing import Optional, TYPE_CHECKING
import functools

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext import associationproxy as ap

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import FormatTypes
from ajbot._internal.types import AjDate
from .base import SaAjDate, BaseWithId, LogMixin
from .season import Season
if TYPE_CHECKING:
    from .member import Member



@functools.total_ordering
class Event(BaseWithId, LogMixin):
    """ Event table class
    """
    __tablename__ = 'events'

    date: orm.Mapped[AjDate] = orm.mapped_column(SaAjDate, nullable=False, index=True, unique=True)
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.id'), nullable=False, index=True)
    season: orm.Mapped['Season'] = orm.relationship(back_populates='events', foreign_keys=season_id, lazy='selectin')
    name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    description: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))

    member_event_associations: orm.Mapped[list['MemberEvent']] = orm.relationship(back_populates='event', foreign_keys='MemberEvent.event_id', lazy='selectin')
    members: ap.AssociationProxy[list['Member']] = ap.association_proxy('member_event_associations','member',
                                                                        creator=lambda event_obj: MemberEvent(event=event_obj),)


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

    def __format__(self, format_spec):
        """ override format
        """
        attr = [self.date, self.name]
        match format_spec:
            case FormatTypes.RESTRICTED:
                pass

            case FormatTypes.FULL:
                attr.append(f"saison {self.season.name}")
                attr.append(f"{len(self.members)} participant(s)")

            case FormatTypes.DEBUG:
                attr.insert(0, f"{self.id}")
                attr.append(f"saison {self.season.name}")
                attr.append(f"{len(self.members)} participant(s) ({', '.join(str(m.id) if m else 'inconnu(e)' for m in self.members)})")

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

        return ' - '.join(f"{x}" for x in attr if x)

# many-to-many association tables
#################################

class MemberEvent(BaseWithId, LogMixin):
    """ Junction table between events and members
    """
    __tablename__ = 'JCT_event_member'
    __table_args__ = (
        sa.UniqueConstraint('event_id', 'member_id',
                            comment='each member can only be present once per event'),
    )

    event_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('events.id'), index=True, nullable=False)
    event: orm.Mapped['Event'] = orm.relationship(back_populates='member_event_associations', foreign_keys=event_id, lazy='selectin')
    member_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=True, comment='Can be null name/id is lost.')
    member: orm.Mapped['Member'] = orm.relationship(back_populates='event_member_associations', foreign_keys=member_id, lazy='selectin')
    presence: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=True, comment='if false: delegated vote')
    comment: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255))

    def __format__(self, format_spec):
        """ override format
        """
        event_member = f"évènement {self.event_id}, membre {self.member_id}"
        match format_spec:
            case FormatTypes.RESTRICTED:
                name_list = ['#####']

            case FormatTypes.FULL:
                name_list = [event_member]

            case FormatTypes.DEBUG:
                name_list = [self.id, '-', event_member]

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

        return ' '.join([f"{x}" for x in name_list if x])


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
