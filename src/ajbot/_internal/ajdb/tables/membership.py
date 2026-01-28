''' membership db table
'''
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy import orm


from ajbot._internal.exceptions import AjDbException
from ajbot._internal.config import FormatTypes
from ajbot._internal.types import AjDate
from .base import SaAjDate, BaseWithId, LogMixin
from .season import Season
if TYPE_CHECKING:
    from .member import Member
    from .lookup import ContributionType, KnowFromSource



class Membership(BaseWithId, LogMixin):
    """ Membership table class
    """
    __tablename__ = 'memberships'
    __table_args__ = (
        sa.UniqueConstraint('season_id', 'member_id',
                            comment='each member can have only one membership per season'),
    )

    date: orm.Mapped[AjDate] = orm.mapped_column(SaAjDate, nullable=False, comment='coupling between this and season')
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship(back_populates='memberships', foreign_keys=member_id, lazy='selectin')
    season_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('seasons.id'), index=True, nullable=False)
    season: orm.Mapped['Season'] = orm.relationship(back_populates='memberships', foreign_keys=season_id, lazy='selectin')
    is_in_current_season: orm.Mapped[bool] = orm.column_property(sa.exists().where(
                    sa.and_(
                        Season.id == season_id,
                        Season.is_current_season)))

    statutes_accepted: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)
    has_civil_insurance: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)
    picture_authorized: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False)

    know_from_source_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('LUT_know_from_sources.id'), index=True, nullable=True)
    know_from_source: orm.Mapped[Optional['KnowFromSource']] = orm.relationship(back_populates='memberships', foreign_keys=know_from_source_id, lazy='selectin')
    contribution_type_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('LUT_contribution_types.id'), index=True, nullable=False)
    contribution_type: orm.Mapped['ContributionType'] = orm.relationship(back_populates='memberships', foreign_keys=contribution_type_id, lazy='selectin')
    # transactions: orm.Mapped[list['Transaction']] = orm.relationship(back_populates='memberships')

    def __format__(self, format_spec):
        """ override format
        """
        member_format = format_spec if format_spec != FormatTypes.DEBUG else FormatTypes.FULL
        member_season = f"membre {self.member:{member_format}} pour la **saison {self.season:{format_spec}}**"
        membership_date = f"cotisé le {self.date}"
        statutes = "- statuts" + (" __**non**__" if not self.statutes_accepted else "") + " acceptés"
        civil = "- assurance civile" + (" __**non**__" if not self.has_civil_insurance else "") + " fournie"
        picture = "- droit à l'image" + (" __**non**__" if not self.picture_authorized else "") + " accordé"

        match format_spec:
            case FormatTypes.RESTRICTED:
                name_list = ['****']

            case FormatTypes.FULL:
                name_list = [member_season, membership_date, statutes, civil, picture]

            case FormatTypes.DEBUG:
                name_list = [f"{self.id} - {member_season}", membership_date, statutes, civil, picture]

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

        return '\n    '.join([f"{x}" for x in name_list if x])
