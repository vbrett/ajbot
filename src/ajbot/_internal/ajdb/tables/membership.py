''' membership db table
'''
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy import orm


from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import FormatTypes
from .base import HumanizedDate, SaHumanizedDate, Base, LogMixin
from .season import Season
if TYPE_CHECKING:
    from .member import Member
    from .lookup import ContributionType, KnowFromSource



class Membership(Base, LogMixin):
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
    member: orm.Mapped['Member'] = orm.relationship(back_populates='memberships', lazy='selectin')
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.id'), index=True, nullable=False)
    season: orm.Mapped['Season'] = orm.relationship(back_populates='memberships', lazy='selectin')
    is_in_current_season: orm.Mapped[bool] = orm.column_property(sa.exists().where(
                    sa.and_(
                        Season.id == season_id,
                        Season.is_current_season)))

    statutes_accepted: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)
    has_civil_insurance: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)
    picture_authorized: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)

    know_from_source_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('LUT_know_from_sources.id'), index=True, nullable=True)
    know_from_source: orm.Mapped[Optional['KnowFromSource']] = orm.relationship(back_populates='memberships', lazy='selectin')
    contribution_type_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('LUT_contribution_types.id'), index=True, nullable=False)
    contribution_type: orm.Mapped['ContributionType'] = orm.relationship(back_populates='memberships', lazy='selectin')
    # transactions: orm.Mapped[list['Transaction']] = orm.relationship(back_populates='memberships')
    # logs: orm.Mapped[list['Log']] = orm.relationship(back_populates='memberships', lazy='selectin')

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """

        match format_spec:
            case FormatTypes.RESTRICTED:
                return '****'

            case FormatTypes.FULLSIMPLE | FormatTypes.FULLCOMPLETE:
                season_name = f"**saison {self.season:{format_spec}}**"
                membership_date = f"cotisé le {self.date}"
                statutes = "- statuts" + (" __**non**__" if not self.statutes_accepted else "") + " acceptés"
                civil = "- assurance civile" + (" __**non**__" if not self.has_civil_insurance else "") + " fournie"
                picture = "- droit à l'image" + (" __**non**__" if not self.picture_authorized else "") + " accordé"
                return '\n'.join(x for x in [season_name, membership_date, statutes, civil, picture] if x)

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
