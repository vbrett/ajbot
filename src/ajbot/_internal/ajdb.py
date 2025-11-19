''' manage AJ database

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
then manually reformated
'''
import sqlalchemy as sa
from sqlalchemy.ext import asyncio as aio_sa

import discord
from discord.ext.commands import MemberNotFound

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import AjConfig
from ajbot._internal import ajdb_tables as ajdb_t



class AjDb():
    """ Context manager which manage AJ database
        Create DB engine and async session maker on enter, and dispose engine on exit
    """
    def __init__(self):
        self.db_engine = None
        self.AsyncSessionMaker = None   #pylint: disable=invalid-name   #variable is a class factory
        self.db_username = None

    async def __aenter__(self):
        with AjConfig(save_on_exit=False, break_if_missing=True) as aj_config:
            self.db_username = aj_config.db_creds['user']
            # Connect to MariaDB Platform
            self.db_engine = aio_sa.create_async_engine("mysql+aiomysql://" + aj_config.db_connection_string,
                                                        echo=aj_config.db_echo)

        # aio_sa.async_sessionmaker: a factory for new AsyncSession objects
        # expire_on_commit - don't expire objects after transaction commit
        self.AsyncSessionMaker = aio_sa.async_sessionmaker(bind = self.db_engine, expire_on_commit=False)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        # for AsyncEngine created in function scope, close and
        # clean-up pooled connections
        await self.db_engine.dispose()
        self.db_username = None
        self.AsyncSessionMaker = None

    # DB Management
    # =============
    async def drop_create_schema(self):
        """ recreate database schema
        """
        if self.db_username != 'ajadmin':
            raise AjDbException(f"L'utilisateur {self.db_username} ne peut pas recréer la base de donnée !")
        # create all tables
        async with self.db_engine.begin() as conn:
            await conn.run_sync(ajdb_t.Base.metadata.drop_all)
            await conn.run_sync(ajdb_t.Base.metadata.create_all)

    # DB Queries
    # ==========

    async def get_table_content(self, tables):
        ''' retrieve complete tables
            @arg: list of table classes to retrieve

            @return
                [all found rows]
        '''
        query = sa.select(*tables)
        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        return query_result.scalars().all()

    async def get_members(self,
                     lookup_val = None,
                     match_crit = 50,
                     break_if_multi_perfect_match = True,):
        ''' retrieve list of member ids matching lookup_val which can be
                - discord member object
                - integer = member ID
                - string that is compared to "user friendly name" using fuzzy search
                - None: return all members

            for first 2 types, return exact match
            for last, return exact match if found, otherwise list of match above match_crit
            In case of multiple perfect match, raise exception if asked

            @return
                [member (if perfect match) or matchedMember (if not perfect match)]
        '''
        query = None
        if not lookup_val:
            query = sa.select(ajdb_t.Member)

        # Check if lookup_val is a discord.ajdb_t.Member object
        if isinstance(lookup_val, discord.Member):
            try:
                query = sa.select(ajdb_t.Member).join(ajdb_t.Member.discord_pseudo).where(ajdb_t.DiscordPseudo.name == lookup_val.name)
            except MemberNotFound as e:
                raise AjDbException(f'Le champ de recherche {lookup_val} n\'est pas reconnu comme de type discord') from e

        # check if lookup_val is an integer (member ID)
        elif isinstance(lookup_val, int):
            query = sa.select(ajdb_t.Member).where(ajdb_t.Member.id == lookup_val)

        elif isinstance(lookup_val, str):
            query = sa.select(ajdb_t.Member).where(ajdb_t.Member.credential)

        else:
            raise AjDbException(f'Le champ de recherche doit être de type "discord", "int" or "str", pas "{type(lookup_val)}"')


        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        matched_members = query_result.scalars().all()

        if len(matched_members) <= 1:
            return matched_members

        # Fuzz search on credential
        for v in matched_members:
            v.credential.fuzzy_lookup = lookup_val

        perfect_match = [v for v in matched_members if v.credential.fuzzy_match == 100]
        if perfect_match:
            if len(perfect_match) > 1 and break_if_multi_perfect_match:
                raise AjDbException(f"Plusieurs correspondances parfaites pour {lookup_val}")
            return perfect_match

        matched_members = [v for v in matched_members if v.credential.fuzzy_match > match_crit]
        matched_members.sort(key=lambda x: x.credential.fuzzy_match, reverse=True)
        return matched_members

    async def get_season_subscribers(self, season_name = None):
        ''' retrieve list of member having subscribed to season
            @args
                season_name = Optional. If empty, use current season

            @return
                [all found Members]
        '''
        if season_name:
            query = sa.select(ajdb_t.Member).join(ajdb_t.Membership).join(ajdb_t.Season).where(ajdb_t.Season.name == season_name)
        else:
            query = sa.select(ajdb_t.Member).join(ajdb_t.Membership).where(ajdb_t.Membership.is_in_current_season)
        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        return query_result.scalars().all()

    async def get_season_events(self, season_name = None):
        ''' retrieve list of events having occured in season
            @args
                season_name = Optional. If empty, use current season

            @return
                [all found events]
        '''
        if season_name:
            query = sa.select(ajdb_t.Event).join(ajdb_t.Season).where(ajdb_t.Season.name == season_name)
        else:
            query = sa.select(ajdb_t.Event).where(ajdb_t.Event.is_in_current_season)
        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        return query_result.scalars().all()

    async def get_season_members(self, season_name = None):
        ''' retrieve list of members having participated in season
            @args
                season_name = Optional. If empty, use current season

            @return
                [all found members with number of presence]
        '''
        if season_name:
            query = sa.select(ajdb_t.Member)\
                        .join(ajdb_t.MemberEvent)\
                        .join(ajdb_t.Event)\
                        .join(ajdb_t.Season)\
                        .where(ajdb_t.Season.name == season_name)\
                        .group_by(ajdb_t.Member)
        else:
            query = sa.select(ajdb_t.Member)\
                        .join(ajdb_t.MemberEvent)\
                        .join(ajdb_t.Event)\
                        .join(ajdb_t.Season)\
                        .where(ajdb_t.Season.is_current_season)\
                        .group_by(ajdb_t.Member)

        async with self.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        return query_result.scalars().all()



if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
