''' Season db table
'''
from typing import TYPE_CHECKING
import datetime

import sqlalchemy as sa
from sqlalchemy import orm

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import FormatTypes
from ajbot._internal.types import AjDate
from .base import SaAjDate, BaseWithId, LogMixin
if TYPE_CHECKING:
    from .member import Membership, Event

class Season(BaseWithId, LogMixin):
    """ Season table class
    """
    __tablename__ = 'seasons'

    name: orm.Mapped[str] = orm.mapped_column(sa.String(10), nullable=False, index=True)
    start: orm.Mapped[AjDate] = orm.mapped_column(SaAjDate, nullable=False, unique=True)
    end: orm.Mapped[AjDate] = orm.mapped_column(SaAjDate, nullable=False)
    is_current_season: orm.Mapped[bool] = orm.column_property(
                    sa.and_(
                        datetime.datetime.now().date() >= start,
                        sa.or_(end == None,     #pylint: disable=singleton-comparison   #this is SQL syntax
                               datetime.datetime.now().date() <= end)))

    memberships: orm.Mapped[list['Membership']] = orm.relationship(back_populates='season', foreign_keys='Membership.season_id', lazy='selectin')
    events: orm.Mapped[list['Event']] = orm.relationship(back_populates='season', foreign_keys='Event.season_id', lazy='selectin')
    # transactions: orm.Mapped[list['Transaction']] = orm.relationship(back_populates='seasons')

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
        return f"{self}"

    def __format__(self, format_spec):
        """ override format
        """
        dates = f"du {self.start} au {self.end}"
        current = '(en cours)' if self.is_current_season else ''
        # return self.name
        match format_spec:
            case FormatTypes.RESTRICTED:
                name_list = [self.name]

            case FormatTypes.FULLSIMPLE:
                name_list = [self.name, current, dates]

            case FormatTypes.FULLCOMPLETE:
                name_list = [self.id, self.name,current, dates]

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

        return ' '.join([f"{x}" for x in name_list if x])

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
