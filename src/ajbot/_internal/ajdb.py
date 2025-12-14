''' manage AJ database

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
then manually reformated
'''
from functools import wraps
from typing import cast, Optional
from datetime import date, datetime,timedelta
from contextlib import nullcontext

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext import asyncio as aio_sa

import discord
from discord.ext.commands import MemberNotFound

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import AjConfig
from ajbot._internal import ajdb_tables as ajdb_t

def cached_ajdb_method(func):
    """ Decorator to handle cached AjDb data
    @arg:
        refresh_cache: if True, refresh cache even if not expired
        keep_detached: if False, merge cached data with current session to avoid DetachedInstanceError
    @return:
        cached data if available and not expired
    """
    cache_data = {}
    cache_time = {}

    @wraps(func)
    async def wrapper(self, *args, refresh_cache:bool=False, keep_detached:bool=False, **kwargs):
        key = (func.__name__, args, tuple(kwargs.items()))
        now = datetime.now()
        if not refresh_cache:
            with AjConfig() if not self.aj_config else nullcontext(self.aj_config) as aj_config:
                if key in cache_data and now - cache_time[key] < timedelta(seconds=aj_config.db_cache_time_sec):
                    if not keep_detached:
                        # merge cached data with current session to avoid DetachedInstanceError
                        if isinstance(cache_data[key], list):
                            for i, v in enumerate(cache_data[key]):
                                cache_data[key][i] = await self.aio_session.merge(v, load=False)
                        else:
                            cache_data[key] = await self.aio_session.merge(cache_data[key], load=False)
                    return cache_data[key]

        result = await func(self, *args, **kwargs)

        cache_data[key] = result
        cache_time[key] = now
        return result
    return wrapper


class AjDb():
    """ Context manager which manage AJ database
        Create DB engine and async session maker on enter, and dispose engine on exit
    """
    def __init__(self, aj_config:AjConfig=None):
        self.db_engine: aio_sa.AsyncEngine = None
        self.db_username:str = None
        self.AsyncSessionMaker:aio_sa.async_sessionmaker = None   #pylint: disable=invalid-name   #variable is a class factory
        self.aio_session: aio_sa.async_sessionmaker[aio_sa.AsyncSession] = None
        self.aj_config = aj_config

    async def __aenter__(self):
        with AjConfig() if not self.aj_config else nullcontext(self.aj_config) as aj_config:
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
        try:
            await self.aio_session.commit()
        except Exception:
            await self.aio_session.rollback()
            raise
        finally:
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

    # General
    # -------
    @cached_ajdb_method
    async def query_table_content(self, table, *options):
        ''' retrieve complete table
            @arg:
                class of the table to retrieve
                options: options to pass to query (typically, load strategy override)

            @return
                [all found rows]
        '''

        query = sa.select(table)
        if options:
            for option in options:
                query = query.options(option)
        query_result = await self.aio_session.execute(query)
        query_result = query_result.scalars().all()

        return query_result


    @cached_ajdb_method
    async def query_seasons(self, lazyload:bool=True):
        ''' retrieve list of seasons
            @args
                lazyload = if True, use lazyload for events and memberships

            @return
                [all found seasons]
        '''
        query = sa.select(ajdb_t.Season)
        if lazyload:
            query = query.options(orm.lazyload(ajdb_t.Season.events), orm.lazyload(ajdb_t.Season.memberships))
        else:
            query = query.options(orm.selectinload(ajdb_t.Season.events), orm.selectinload(ajdb_t.Season.memberships))

        query_result = await self.aio_session.execute(query)
        query_result = query_result.scalars().all()

        return query_result

    @cached_ajdb_method
    async def query_asso_roles(self, lazyload:bool=True):
        ''' retrieve list of asso roles
            @args
                lazyload = if True, use lazyload for events and memberships

            @return
                [all found roles]
        '''
        query = sa.select(ajdb_t.AssoRole)
        if lazyload:
            query = query.options(orm.lazyload(ajdb_t.AssoRole.discord_roles), orm.lazyload(ajdb_t.AssoRole.members, ajdb_t.MemberAssoRole.member))
        else:
            query = query.options(orm.selectinload(ajdb_t.AssoRole.discord_roles), orm.selectinload(ajdb_t.AssoRole.members, ajdb_t.MemberAssoRole.member))

        query_result = await self.aio_session.execute(query)
        query_result = query_result.scalars().all()

        return query_result


    async def query_discord_asso_roles(self):
        ''' retrieve list of dicord & asso roles and how their are mapped

            @return
                [all found roles]
        '''
        query = sa.select(ajdb_t.AssoRoleDiscordRole)

        query_result = await self.aio_session.execute(query)
        query_result = query_result.scalars().all()

        return query_result


    # Members
    # -------
    async def query_members(self,
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


    # Events
    # -------
    @cached_ajdb_method
    async def query_events(self, event_str:Optional[str] = None, lazyload:bool=True):
        ''' retrieve all events or with a given name
            @args
                event_str = Optional. if empty, return all events
                lazyload = if True, use lazyload for members

            @return
                [all found events]
        '''
        query = sa.select(ajdb_t.Event)
        if lazyload:
            query = query.options(orm.lazyload(ajdb_t.Event.members, ajdb_t.MemberEvent.member))
        else:
            query = query.options(orm.selectinload(ajdb_t.Event.members, ajdb_t.MemberEvent.member))

        query_result = await self.aio_session.execute(query)

        events = query_result.scalars().all()
        if event_str:
            events = [e for e in events if str(e) == event_str]

        return events


    @cached_ajdb_method
    async def query_events_per_season(self, season_name:Optional[str] = None, lazyload:bool=True):
        ''' retrieve list of events having occured in a given season
            @args
                season_name = Optional.if empty, return current season
                lazyload = if True, use lazyload for members

            @return
                [all found events]
        '''
        if season_name:
            query = sa.select(ajdb_t.Event).join(ajdb_t.Season).where(ajdb_t.Season.name == season_name)
        else:
            query = sa.select(ajdb_t.Event).where(ajdb_t.Event.is_in_current_season)
        if lazyload:
            query = query.options(orm.lazyload(ajdb_t.Event.members, ajdb_t.MemberEvent.member))
        else:
            query = query.options(orm.selectinload(ajdb_t.Event.members, ajdb_t.MemberEvent.member))

        query_result = await self.aio_session.execute(query)

        events = query_result.scalars().all()

        return events


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
            raise AjDbException(f'ID asso inconnu(s): {', '.join(str(i) for i in unkown_participant_ids)}')

        # create or get event
        if not event_id:
            if not event_date:
                raise AjDbException('Evnènement ou date manquante.')
            db_event = ajdb_t.Event(date=event_date)
            seasons = await self.query_seasons(lazyload=True)
            [db_event.season_id] = [s.id for s in seasons if db_event.date >= s.start and db_event.date <= s.end]
            self.aio_session.add(db_event)
        else:
            query = sa.select(ajdb_t.Event).where(ajdb_t.Event.id == event_id)
            query_result = await self.aio_session.execute(query)
            db_event = query_result.scalars().one_or_none()
            if not db_event:
                raise AjDbException(f'Evènement inconnu: {event_id}')

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
