''' Season db table
'''
from typing import TYPE_CHECKING
import datetime

import sqlalchemy as sa
from sqlalchemy import orm

from ajbot._internal.exceptions import OtherException
from .base import HumanizedDate, SaHumanizedDate, Base, LogMixin
if TYPE_CHECKING:
    from .member import Membership, Event

class Season(Base, LogMixin):
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

    memberships: orm.Mapped[list['Membership']] = orm.relationship(back_populates='season', lazy='selectin')
    events: orm.Mapped[list['Event']] = orm.relationship(back_populates='season', lazy='selectin')
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

    def __format__(self, _format_spec):
        """ override format
        """
        return self.name

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
