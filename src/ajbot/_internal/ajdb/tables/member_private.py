''' Member private db tables
'''
from typing import Optional, TYPE_CHECKING
import functools

import sqlalchemy as sa
from sqlalchemy import orm

from thefuzz import fuzz

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import FormatTypes
from .base import HumanizedDate, SaHumanizedDate, Base, LogMixin
if TYPE_CHECKING:
    from .member import Member
    from .lookup import StreetType



@functools.total_ordering
class Credential(Base, LogMixin):
    """ user credential table class
    """
    __tablename__ = 'member_credentials'
    __table_args__ = (
                      sa.UniqueConstraint('first_name', 'last_name', 'birthdate'),
                      {'comment': 'contains RGPD info'},
                     )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    member: orm.Mapped[Optional['Member']] = orm.relationship(back_populates='credential', foreign_keys='Member.credential_id', uselist=False, lazy='selectin')
    first_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    last_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50))
    birthdate: orm.Mapped[Optional[HumanizedDate]] = orm.mapped_column(SaHumanizedDate)

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

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        mbr_match = f"({self.fuzzy_match}%)" if self.fuzzy_match < 100 else None
        match format_spec:
            case FormatTypes.RESTRICTED:
                name_list = [self.first_name, mbr_match]

            case FormatTypes.FULLSIMPLE:
                name_list = [self.first_name, self.last_name, mbr_match]

            case FormatTypes.FULLCOMPLETE:
                name_list = [self.first_name, self.last_name, mbr_match, self.birthdate]

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")

        return ' '.join([f"{x}" for x in name_list if x])


class Email(Base, LogMixin):
    """ user email table class
    """
    __tablename__ = 'member_emails'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    address: orm.Mapped[str] = orm.mapped_column(sa.String(50), nullable=False, unique=True, index=True)

    members: orm.Mapped[list['MemberEmail']] = orm.relationship(back_populates='email', foreign_keys='MemberEmail.email_id', lazy='selectin')

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.RESTRICTED:
                return 'xxxxxx@yyyy.zzz'

            case FormatTypes.FULLSIMPLE | FormatTypes.FULLCOMPLETE:
                return self.address

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")


class Phone(Base, LogMixin):
    """ user phone number table class
    """
    __tablename__ = 'member_phones'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    number: orm.Mapped[str] = orm.mapped_column(sa.String(20), unique=True, index=True, nullable=False)

    members: orm.Mapped[list['MemberPhone']] = orm.relationship(back_populates='phone', foreign_keys='MemberPhone.phone_id', lazy='selectin')

    def __str__(self):
        return f"{self}"

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.RESTRICTED:
                return '(+33)000000000'

            case FormatTypes.FULLSIMPLE | FormatTypes.FULLCOMPLETE:
                return self.number

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")


class PostalAddress(Base, LogMixin):
    """ user address table class
    """
    __tablename__ = 'member_addresses'
    __table_args__ = (
        sa.UniqueConstraint('street_num', 'street_type_id', 'street_name', 'zip_code', 'city',),
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, index=True, autoincrement=True)
    street_num: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(50), nullable=True)
    street_type_id: orm.Mapped[Optional[int]] = orm.mapped_column(sa.ForeignKey('LUT_street_types.id'), index=True, nullable=True)
    street_type: orm.Mapped[Optional['StreetType']] = orm.relationship(back_populates='addresses', foreign_keys='PostalAddress.street_type_id', lazy='selectin')
    street_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)
    zip_code: orm.Mapped[Optional[int]] = orm.mapped_column(sa.Integer, nullable=True)
    city: orm.Mapped[str] = orm.mapped_column(sa.String(255), nullable=False)
    extra: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(255), nullable=True)

    members: orm.Mapped[list['MemberAddress']] = orm.relationship(back_populates='address', foreign_keys='MemberAddress.address_id', lazy='selectin')

    def __str__(self):
        return format(self, FormatTypes.RESTRICTED)

    def __format__(self, format_spec):
        """ override format
        """
        match format_spec:
            case FormatTypes.RESTRICTED:
                return self.city

            case FormatTypes.FULLSIMPLE | FormatTypes.FULLCOMPLETE:
                return ' '.join([f"{x}" for x in [self.street_num,
                                                  self.street_type,
                                                  self.street_name,
                                                  self.zip_code,
                                                  self.city,
                                                  self.extra] if x])

            case _:
                raise AjDbException(f"Le format {format_spec} n'est pas supporté")



# many-to-many association tables
#################################

class MemberEmail(Base, LogMixin):
    """ Junction table between members and emails
    """
    __tablename__ = 'JCT_member_email'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship(back_populates='emails', foreign_keys=member_id, lazy='selectin')
    email_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_emails.id'), index=True, nullable=False)
    email: orm.Mapped['Email'] = orm.relationship(back_populates='members', foreign_keys=email_id, lazy='selectin')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')

    def __str__(self):
        return f"{self.id}, member #{self.member_id}, email #{self.email_id}"


class MemberPhone(Base, LogMixin):
    """ Junction table between members and phones
    """
    __tablename__ = 'JCT_member_phone'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship(back_populates='phones', foreign_keys=member_id, lazy='selectin')
    phone_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_phones.id'), index=True, nullable=False)
    phone: orm.Mapped['Phone'] = orm.relationship(back_populates='members', foreign_keys=phone_id, lazy='selectin')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')

    def __str__(self):
        return f"{self.id}, member #{self.member_id}, phone #{self.phone_id}"


class MemberAddress(Base, LogMixin):
    """ Junction table between members and addresses
    """
    __tablename__ = 'JCT_member_address'
    __table_args__ = (
        {'comment': 'contains RGPD info'}
    )

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    member_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('members.id'), index=True, nullable=False)
    member: orm.Mapped['Member'] = orm.relationship(back_populates='addresses', foreign_keys=member_id, lazy='selectin')
    address_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey('member_addresses.id'), index=True, nullable=False)
    address: orm.Mapped['PostalAddress'] = orm.relationship(back_populates='members', foreign_keys=address_id, lazy='selectin')
    principal: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, nullable=False, default=False, comment='shall be TRUE for only 1 member_id occurence')

    def __str__(self):
        return f"{self.id}, member #{self.member_id}, address #{self.address_id}"



if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
