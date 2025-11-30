''' manage AJ database

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
then manually reformated
'''
from typing import cast, Optional
from datetime import date


import sqlalchemy as sa
from sqlalchemy import orm
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
        self.db_engine: aio_sa.AsyncEngine = None
        self.db_username:str = None
        self.AsyncSessionMaker:aio_sa.async_sessionmaker = None   #pylint: disable=invalid-name   #variable is a class factory
        self.aio_session: aio_sa.async_sessionmaker[aio_sa.AsyncSession] = None

    async def __aenter__(self):
        with AjConfig() as aj_config:
            self.db_username = aj_config.db_creds['user']
            # Connect to MariaDB Platform
            self.db_engine = aio_sa.create_async_engine("mysql+aiomysql://" + aj_config.db_connection_string,
                                                        echo=aj_config.db_echo)

        # aio_sa.async_sessionmaker: a factory for new AsyncSession objects
        # expire_on_commit - don't expire objects after transaction commit
        self.AsyncSessionMaker = aio_sa.async_sessionmaker(bind = self.db_engine, expire_on_commit=False)
        self.aio_session = self.AsyncSessionMaker()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        # Commit & close session, flushing all pending changes
        await self.aio_session.commit()
        await self.aio_session.close()
        self.aio_session = None
        # Close and clean-up pooled connections
        await self.db_engine.dispose()
        self.AsyncSessionMaker = None
        self.db_username = None


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

    async def query_table_content(self, table):
        ''' retrieve complete table
            @arg:
                class of the table to retrieve

            @return
                [all found rows]
        '''
        query = sa.select(table)
        query_result = await self.aio_session.execute(query)

        return query_result.scalars().all()

    async def query_members_per_id_info(self,
                     lookup_val = None,
                     match_crit = 50,
                     break_if_multi_perfect_match = True,):
        ''' retrieve list of members matching lookup_val which can be
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


        query_result = await self.aio_session.execute(query)

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

    async def query_events(self, season_name:Optional[str] = None,
                                 event_str:Optional[str] = None):
        ''' retrieve list of events having occured in a given season
            @args
                season_name = Optional
                event_str = Optional

                if both empty, return current season
                if none empty, raise an error

            @return
                [all found events]
        '''
        if season_name and event_str:
            raise AjDbException('Both season & event name are provided. Only one shall')

        if event_str:
            query = sa.select(ajdb_t.Event)
        elif season_name:
            query = sa.select(ajdb_t.Event).join(ajdb_t.Season).where(ajdb_t.Season.name == season_name)
        else:
            query = sa.select(ajdb_t.Event).where(ajdb_t.Event.is_in_current_season)
        query = query.options(orm.selectinload(ajdb_t.Event.members, ajdb_t.MemberEvent.member))

        query_result = await self.aio_session.execute(query)

        events = query_result.scalars().all()
        if event_str:
            events = [e for e in events if str(e) == event_str]

        return events

    async def query_members_per_season_presence(self, season_name = None, subscriber_only = False):
        ''' retrieve list of members having participated in season
            @args
                season_name     [Optional] If empty, use current season
                subscriber_only [Optional] If True return only people that have subscribed

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

        query_result = await self.aio_session.execute(query)

        members = query_result.scalars().all()
        if subscriber_only:
            members = [m for m in members
                       if any(mb for mb in cast(ajdb_t.Member, m).memberships
                              if ((not season_name and mb.is_in_current_season and mb.member == m)
                                  or mb.is_in_current_season and mb.season.name == season_name))]
        return members

    async def query_members_per_event_presence(self, event_id):
        ''' retrieve list of members having participated to an event
            @args
                event_id
            @return
                [all found members with number of presence]
        '''
        query = sa.select(ajdb_t.Member)\
                    .join(ajdb_t.MemberEvent)\
                    .join(ajdb_t.Event)\
                    .where(ajdb_t.Event.id == event_id)\
                    .group_by(ajdb_t.Member)

        query_result = await self.aio_session.execute(query)

        return query_result.scalars().all()


    async def add_update_event(self,
                               event_id = None,
                               event_date:Optional[date]=None,
                               event_name:Optional[str]=None,
                               participant_ids:Optional[list[int]]=None,):
        """ add or update an event
        """
        query = sa.select(sa.func.max(ajdb_t.Member.id))
        query_result = await self.aio_session.execute(query)
        last_valid_member_id = query_result.scalars().one_or_none()
        unkown_participant_ids = [i for i in participant_ids if i > last_valid_member_id]

        if unkown_participant_ids:
            raise AjDbException(f'Unknown participant ids: {', '.join(str(i) for i in unkown_participant_ids)}')

        # create or get event
        if not event_id:
            if not event_date:
                raise AjDbException('Missing event id or date.')
            db_event = ajdb_t.Event(date=event_date)
            seasons = await self.query_table_content(ajdb_t.Season)
            [db_event.season] = [s for s in seasons if db_event.date >= s.start and db_event.date <= s.end]
            self.aio_session.add(db_event)
        else:
            query = sa.select(ajdb_t.Event).where(ajdb_t.Event.id == event_id)
            query_result = await self.aio_session.execute(query)
            db_event = query_result.scalars().one_or_none()
            if not db_event:
                raise AjDbException(f'Unknown event to update: {event_id}')

        # set name
        db_event.name = event_name

        # delete / add participants
        for m_e in db_event.members:
            if m_e.member_id not in participant_ids:
                await self.aio_session.delete(m_e)

        existing_participant_ids = [m_e.member_id for m_e in await db_event.awaitable_attrs.members]
        for mbr_id in participant_ids:
            if mbr_id not in existing_participant_ids:
                db_event.members.append(ajdb_t.MemberEvent(member_id = mbr_id))

        await self.aio_session.commit()
        await self.aio_session.refresh(db_event)

        return db_event




if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
