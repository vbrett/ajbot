""" test deployment of a MariaDB instance
"""
import sys
import asyncio
from uuid import UUID, uuid4
from typing import List
from typing import Optional
from datetime import datetime #, date, time

import sqlalchemy as sa
from sqlalchemy.ext import asyncio as aio_sa
from sqlalchemy.orm import selectinload, DeclarativeBase, Mapped, mapped_column, relationship

from ajbot._internal.config import AjConfig


class Base(aio_sa.AsyncAttrs, DeclarativeBase):
    """ Base ORM class
    """

class User(Base):
    """ user account table class
    """
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, unique=True)
    creation_date: Mapped[datetime] = mapped_column(server_default=datetime.now())
    last_name: Mapped[Optional[str]] = mapped_column(sa.String(50))
    first_name: Mapped[Optional[str]] = mapped_column(sa.String(50))
    emails: Mapped[List["Emails"]] = relationship(
        back_populates="users", cascade="all, delete-orphan"
    )
    discord: Mapped[Optional[str]] = mapped_column(sa.String(50))
    # addresses: Mapped[List["Address"]] = relationship(
    #     back_populates="user", cascade="all, delete-orphan"
    # )

    def __repr__(self) -> str:
        return f"{self}"

    def __format__(self, format_spec="simple"):
        """ override format
        """
        match format_spec:
            case "full":
                member_info = [f"{self.id}",
                               " ".join([self.first_name, self.last_name]) if self.first_name or self.last_name else None,
                               f"@{self.discord}" if self.discord else None,
                              ]
                return " - ".join([x for x in member_info if x])

            case "simple":
                member_info = [self.first_name if self.first_name else None,
                               f"@{self.discord}" if self.discord else None,
                              ]
                return " - ".join([x for x in member_info if x])

            case _:
                return "this format is not supported (yet)"

class Emails(Base):
    """ user account table class
    """
    __tablename__ = "emails"
    id: Mapped[UUID] = mapped_column(primary_key=True, unique=True, server_default=uuid4())
    email: Mapped[str] = mapped_column(sa.String(50), index=True, unique=True)
    user_id: Mapped[int] = mapped_column(sa.ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="emails")


# class Address(Base):
#     __tablename__ = "address"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     email_address: Mapped[str]
#     user_id: Mapped[int] = mapped_column(sa.ForeignKey("user_account.id"))
#     user: Mapped["User"] = relationship(back_populates="addresses")
#     def __repr__(self) -> str:
#         return f"Address(id={self.id!r}, email_address={self.email_address!r})"



async def _main():
    """ main function
    """
    with AjConfig(break_if_missing=True,
                  save_on_exit=False,       #TODO: change to True
                 ) as aj_config:

        # Connect to MariaDB Platform
        db_engine = aio_sa.create_async_engine("mysql+aiomysql://" + aj_config.db_connection_string,
                                        echo=True)

        # aio_sa.async_sessionmaker: a factory for new AsyncSession objects
        # expire_on_commit - don't expire objects after transaction commit
        async_session = aio_sa.async_sessionmaker(bind = db_engine, expire_on_commit=False)

        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        new_user = User(first_name="Machin")

        async with async_session.begin() as session:
            session.add(new_user)

        async with async_session.begin() as session:
            query = sa.select(User).options(selectinload(User.emails)).limit(1)
            query_result = await session.execute(query)
            for qr in query_result.scalars():
                print(qr)

        # for AsyncEngine created in function scope, close and
        # clean-up pooled connections
        await db_engine.dispose()

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
