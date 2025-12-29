''' Discord tables
'''
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import FormatTypes
from ajbot._internal.ajdb.support import Base
if TYPE_CHECKING:
    from ajbot._internal.ajdb.tables import Member, AssoRole



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
    member: orm.Mapped['Member'] = orm.relationship(back_populates='discord_pseudo', uselist=False, lazy='selectin')

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


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
