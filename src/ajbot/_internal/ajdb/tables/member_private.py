''' Member private db tables
'''
from typing import Optional, TYPE_CHECKING
import functools

import sqlalchemy as sa
from sqlalchemy import orm

from thefuzz import fuzz

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import FormatTypes
from ajbot._internal.types import AjDate
from .base import SaAjDate, BaseWithId, LogMixin
if TYPE_CHECKING:
    from .member import Member
    from .lookup import StreetType



@functools.total_ordering
class Credential(BaseWithId, LogMixin):
    """ user credential table class
    """
    __tablename__ = 'member_credentials'
    __table_args__ = (
                      sa.UniqueConstraint('first_name', 'last_name', 'birthdate'),
                      {'comment': 'contains RGPD info'},
                     )

    member: orm.Mapped[Optional['Member']] = orm.relationship(back_populates='credential', foreign_keys='Member.credential_id', uselist=False, lazy='selectin')
    first_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    last_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    birthdate: orm.Mapped[Optional[AjDate]] = orm.mapped_column(SaAjDate)

    @orm.reconstructor
    def __init__(self):
        self._fuzzy_lookup = None


    @property
    def fuzzy_lookup(self):
        """ Get the lookup value.
        """
        return self._fuzzy_lookup
    @fuzzy_lookup.setter
    def fuzzy_lookup(self, value):
        """ Set the lookup value.
        """
        self._fuzzy_lookup = value

    @property
    def fuzzy_match(self):
        """ return the matching percentage of credential against the lookup value
            if no lookup, return 100%
        """
        return 100 if not self._fuzzy_lookup else fuzz.token_sort_ratio(self._fuzzy_lookup, self.first_name + ' ' + self.last_name)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        try:
            return ((self.last_name.lower(), self.first_name.lower()) ==
                    (other.last_name.lower(), other.first_name.lower()))
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        try:
            return ((self.last_name.lower(), self.first_name.lower()) <
                    (other.last_name.lower(), other.first_name.lower()))
        except AttributeError:
            return NotImplemented

    def __format__(self, format_spec):
        """ override format
        """
        mbr_match = f"({self.fuzzy_match}%)" if self.fuzzy_match < 100 else None
        match format_spec:
            case FormatTypes.RESTRICTED:
                name_list = [self.first_name, mbr_match]

            case FormatTypes.FULL:
                name_list = [self.last_name, self.first_name, mbr_match]

            case FormatTypes.DEBUG:
                name_list = [self.id, '-', self.last_name, self.first_name, mbr_match, self.birthdate]

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

        return ' '.join([f"{x}" for x in name_list if x])


class Email(BaseWithId, LogMixin):
    """ user email table class
    """
    __tablename__ = 'member_emails'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    address: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, unique=True, index=True)

    members: orm.Mapped[list['MemberEmail']] = orm.relationship(back_populates='email', foreign_keys='MemberEmail.email_id', lazy='selectin')

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.RESTRICTED:
                return 'xxxxxx@yyyy.zzz'

            case FormatTypes.FULL:
                return self.address

            case FormatTypes.DEBUG:
                return f"{self.id} - {self.address}"

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")


class Phone(BaseWithId, LogMixin):
    """ user phone number table class
    """
    __tablename__ = 'member_phones'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    number: orm.Mapped[str] = orm.mapped_column(sa.String(20), unique=True, index=True, nullable=False)

    members: orm.Mapped[list['MemberPhone']] = orm.relationship(back_populates='phone', foreign_keys='MemberPhone.phone_id', lazy='selectin')

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.RESTRICTED:
                return '(+33)XXXXXXXXX'

            case FormatTypes.FULL:
                return self.number

            case FormatTypes.DEBUG:
                return f"{self.id} - {self.number}"

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")


class PostalAddress(BaseWithId, LogMixin):
    """ user address table class
    """
    __tablename__ = 'member_addresses'
    __table_args__ = (
        sa.UniqueConstraint('street_num', 'street_type_id', 'street_name', 'zip_code', 'city',),
        {'comment': 'contains RGPD info'}
    )

    street_num: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50), nullable=True)
    street_type_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('LUT_street_types.id'), index=True, nullable=True)
    street_type: orm.Mapped[Optional['StreetType']] = orm.relationship(back_populates='addresses', foreign_keys='PostalAddress.street_type_id', lazy='selectin')
    street_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)
    zip_code: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer, nullable=True)
    city: orm.Mapped[str] = orm.mapped_column(sa.String(255), nullable=False)
    extra: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)

    members: orm.Mapped[list['MemberAddress']] = orm.relationship(back_populates='address', foreign_keys='MemberAddress.address_id', lazy='selectin')

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.RESTRICTED:
                name_list = [self.city]

            case FormatTypes.FULL:
                name_list = [self.street_num,
                             self.street_type,
                             self.street_name,
                             self.zip_code,
                             self.city,
                             self.extra]

            case FormatTypes.DEBUG:
                name_list = [self.id, '-',
                             self.street_num,
                             self.street_type,
                             self.street_name,
                             self.zip_code,
                             self.city,
                             self.extra]

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

        return ' '.join([f"{x}" for x in name_list if x])



# many-to-many association tables
#################################

class MemberEmail(BaseWithId, LogMixin):
    """ Junction table between members and emails
    """
    __tablename__ = 'JCT_member_email'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship(back_populates='emails', foreign_keys=member_id, lazy='selectin')
    email_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_emails.id'), index=True, nullable=False)
    email: orm.Mapped['Email'] = orm.relationship(back_populates='members', foreign_keys=email_id, lazy='selectin')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')

    def __format__(self, format_spec):
        """ override format
        """
        member_email = f"membre {self.member_id}, email {self.email_id}"
        match format_spec:
            case FormatTypes.RESTRICTED:
                name_list = ['#####']

            case FormatTypes.FULL:
                name_list = [member_email]

            case FormatTypes.DEBUG:
                name_list = [self.id, '-', member_email]

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

        return ' '.join([f"{x}" for x in name_list if x])

class MemberPhone(BaseWithId, LogMixin):
    """ Junction table between members and phones
    """
    __tablename__ = 'JCT_member_phone'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship(back_populates='phones', foreign_keys=member_id, lazy='selectin')
    phone_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_phones.id'), index=True, nullable=False)
    phone: orm.Mapped['Phone'] = orm.relationship(back_populates='members', foreign_keys=phone_id, lazy='selectin')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')

    def __format__(self, format_spec):
        """ override format
        """
        member_phone = f"membre {self.member_id}, téléphone {self.phone_id}"
        match format_spec:
            case FormatTypes.RESTRICTED:
                name_list = ['#####']

            case FormatTypes.FULL:
                name_list = [member_phone]

            case FormatTypes.DEBUG:
                name_list = [self.id, '-', member_phone]

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

        return ' '.join([f"{x}" for x in name_list if x])


class MemberAddress(BaseWithId, LogMixin):
    """ Junction table between members and addresses
    """
    __tablename__ = 'JCT_member_address'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship(back_populates='addresses', foreign_keys=member_id, lazy='selectin')
    address_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_addresses.id'), index=True, nullable=False)
    address: orm.Mapped['PostalAddress'] = orm.relationship(back_populates='members', foreign_keys=address_id, lazy='selectin')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')

    def __format__(self, format_spec):
        """ override format
        """
        member_address = f"membre {self.member_id}, adresse {self.address_id}"
        match format_spec:
            case FormatTypes.RESTRICTED:
                name_list = ['#####']

            case FormatTypes.FULL:
                name_list = [member_address]

            case FormatTypes.DEBUG:
                name_list = [self.id, '-', member_address]

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

        return ' '.join([f"{x}" for x in name_list if x])



if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
