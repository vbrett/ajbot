''' manage AJ database

Classes generated using:
sqlacodegen mariadb://user:password@server:port/aj > ./output.py
then manually reformated
'''
from functools import wraps
from typing import Optional
from datetime import date, datetime,timedelta
from contextlib import nullcontext

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext import asyncio as aio_sa

import discord
from discord.ext.commands import MemberNotFound

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import AjConfig
from ajbot._internal.ajdb import tables as db_t

cache_data = {}
cache_time = {}

def _async_cached(func):
    """ Decorator to handle cached AjDb data
    @arg:
        refresh_cache: if True, refresh cache even if not expired
        keep_detached: if False, merge cached data with current session to avoid DetachedInstanceError
    @return:
        cached data if available and not expired
    """

    @wraps(func)
    async def wrapper(self, *args, refresh_cache:bool=False, keep_detached:bool=False, **kwargs):
        global cache_data   #pylint: disable=global-variable-not-assigned   #on purpose, to handle cache
        global cache_time   #pylint: disable=global-variable-not-assigned   #on purpose, to handle cache

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

def _clear_cache():
    global cache_data   #pylint: disable=global-statement   #on purpose, to handle cache
    global cache_time   #pylint: disable=global-statement   #on purpose, to handle cache

    cache_data = {}
    cache_time = {}


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
            await conn.run_sync(db_t.Base.metadata.drop_all)
            await conn.run_sync(db_t.Base.metadata.create_all)

    async def clear_cache(self):
        """ clear db cache
        """
        _clear_cache()

    async def init_cache(self):
        """ pre-load some semi-permanent db table in cache
        """
        await self.clear_cache()
        await self.query_asso_roles(lazyload=False)
        await self.query_seasons(lazyload=True)


    # DB Queries
    # ==========

    # General
    # -------
    @_async_cached
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
        return (await self.aio_session.scalars(query)).all()


    @_async_cached
    async def query_seasons(self, lazyload:bool=True):
        ''' retrieve list of seasons
            @args
                lazyload = if True, use lazyload for season and memberships

            @return
                [all found seasons]
        '''
        query = sa.select(db_t.Season)
        if lazyload:
            query = query.options(orm.lazyload(db_t.Season.events), orm.lazyload(db_t.Season.memberships))
        else:
            query = query.options(orm.selectinload(db_t.Season.events), orm.selectinload(db_t.Season.memberships))

        return (await self.aio_session.scalars(query)).all()

    @_async_cached
    async def query_asso_roles(self, lazyload:bool=True):
        ''' retrieve list of asso roles
            @args
                lazyload = if True, use lazyload for roles and members

            @return
                [all found roles]
        '''
        query = sa.select(db_t.AssoRole)
        if lazyload:
            query = query.options(orm.lazyload(db_t.AssoRole.discord_roles), orm.lazyload(db_t.AssoRole.members))
        else:
            query = query.options(orm.selectinload(db_t.AssoRole.discord_roles), orm.selectinload(db_t.AssoRole.members))

        return (await self.aio_session.scalars(query)).all()


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
            query = sa.select(db_t.Member)

        # Check if lookup_val is a discord.db_t.Member object
        if isinstance(lookup_val, discord.Member):
            try:
                query = sa.select(db_t.Member).where(db_t.Member.discord == lookup_val.name)
            except MemberNotFound as e:
                raise AjDbException(f'Le champ de recherche {lookup_val} n\'est pas reconnu comme de type discord') from e

        # check if lookup_val is an integer (member ID)
        elif isinstance(lookup_val, int):
            query = sa.select(db_t.Member).where(db_t.Member.id == lookup_val)

        elif isinstance(lookup_val, str):
            query = sa.select(db_t.Member).where(db_t.Member.credential)

        else:
            raise AjDbException(f'Le champ de recherche doit être de type "discord", "int" or "str", pas "{type(lookup_val)}"')


        matched_members = (await self.aio_session.scalars(query)).all()

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

        query = sa.select(db_t.Member)
        if subscriber_only:
            query = query.join(db_t.Membership)
        else:
            query = query.join(db_t.MemberEvent).join(db_t.Event)

        if season_name:
            where = db_t.Season.name == season_name
        else:
            where = db_t.Season.is_current_season

        query = query.join(db_t.Season)\
                     .where(where)\
                     .group_by(db_t.Member)

        members = (await self.aio_session.scalars(query)).all()
        return members

    async def query_members_per_event_presence(self, event_id):
        ''' retrieve list of members having participated to an event
            @args
                event_id
            @return
                [all found members with number of presence]
        '''
        query = sa.select(db_t.Member)\
                    .join(db_t.MemberEvent)\
                    .join(db_t.Event)\
                    .where(db_t.Event.id == event_id)\
                    .group_by(db_t.Member)

        return (await self.aio_session.scalars(query)).all()


    # Events
    # -------
    async def query_events(self, event_str:Optional[str] = None, lazyload:bool=True):
        ''' retrieve all events or with a given name
            @args
                event_str = Optional. if empty, return all events
                lazyload = if True, use lazyload for members

            @return
                [all found events]
        '''
        query = sa.select(db_t.Event)
        if lazyload:
            query = query.options(orm.lazyload(db_t.Event.members))
        else:
            query = query.options(orm.selectinload(db_t.Event.members))

        events = (await self.aio_session.scalars(query)).all()
        if event_str:
            events = [e for e in events if str(e) == event_str]

        return events


    async def query_events_per_season(self, season_name:Optional[str] = None, lazyload:bool=True):
        ''' retrieve list of events having occured in a given season
            @args
                season_name = Optional.if empty, return current season
                lazyload = if True, use lazyload for members

            @return
                [all found events]
        '''
        if season_name:
            query = sa.select(db_t.Event).where(db_t.Event.season.has(db_t.Season.name == season_name))
        else:
            query = sa.select(db_t.Event).where(db_t.Event.is_in_current_season)
        if lazyload:
            query = query.options(orm.lazyload(db_t.Event.members))
        else:
            query = query.options(orm.selectinload(db_t.Event.members))

        events = (await self.aio_session.scalars(query)).all()

        return events


    async def add_update_event(self,
                               event_id = None,
                               event_date:Optional[date]=None,
                               event_name:Optional[str]=None,
                               participant_ids:Optional[list[int]]=None,):
        """ add or update an event
        """
        query = sa.select(sa.func.max(db_t.Member.id))
        last_valid_member_id = (await self.aio_session.scalars(query)).one_or_none()
        unkown_participant_ids = [i for i in participant_ids if i > last_valid_member_id]

        if unkown_participant_ids:
            raise AjDbException(f'ID asso inconnu(s): {', '.join(str(i) for i in unkown_participant_ids)}')

        # create or get event
        if not event_id:
            if not event_date:
                raise AjDbException('Evnènement ou date manquante.')
            db_event = db_t.Event(date=event_date)
            seasons = await self.query_table_content(db_t.Season, orm.lazyload(db_t.Season.events), orm.lazyload(db_t.Season.memberships))
            [db_event.season] = [s for s in seasons if db_event.date >= s.start and db_event.date <= s.end]
            self.aio_session.add(db_event)
        else:
            query = sa.select(db_t.Event).where(db_t.Event.id == event_id)
            db_event = (await self.aio_session.scalars(query)).one_or_none()
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
                db_event.members.append(db_t.MemberEvent(member_id = mbr_id))

        await self.aio_session.commit()
        await self.aio_session.refresh(db_event)

        return db_event


    async def add_update_member(self,
                                member_id = None,
                                last_name:Optional[str]=None,
                                first_name:Optional[str]=None,
                                birthdate:Optional[date]=None,
                                discord_name:Optional[str]=None,):
        """ add or update an event
        """

        if not member_id:
            db_member = db_t.Member()
            db_member.credential = db_t.Credential()
            self.aio_session.add(db_member)
        else:
            query = sa.select(db_t.Member).where(db_t.Member.id == member_id)
            db_member = (await self.aio_session.scalars(query)).one_or_none()

        db_member.credential.first_name = first_name
        db_member.credential.last_name = last_name
        db_member.credential.birthdate = birthdate
        db_member.discord = discord_name

        await self.aio_session.commit()
        await self.aio_session.refresh(db_member)

        return db_member



if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
