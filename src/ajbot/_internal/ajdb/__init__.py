''' manage AJ database
'''
from functools import wraps
from typing import Optional
from datetime import date, datetime,timedelta

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from vbrpytools.misctools import divide_list

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext import asyncio as aio_sa

import discord
from discord.ext.commands import MemberNotFound

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import AjConfig, FormatTypes
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
            if key in cache_data and now - cache_time[key] < timedelta(seconds=self._aj_config.db_cache_time_sec): #pylint: disable=protected-access    #this decorator is for this class
                if not keep_detached:
                    # merge cached data with current session to avoid DetachedInstanceError
                    if isinstance(cache_data[key], list):
                        for i, v in enumerate(cache_data[key]):
                            cache_data[key][i] = await self._aio_session.merge(v, load=False)            #pylint: disable=protected-access    #this decorator is for this class
                    else:
                        cache_data[key] = await self._aio_session.merge(cache_data[key], load=False)     #pylint: disable=protected-access    #this decorator is for this class
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
        Configuration file can be provided at init, otherwise default config info will be internally loaded
    """
    def __init__(self, aj_config:AjConfig=None, modifier_discord:Optional[str]=None):
        self._modifier_discord = modifier_discord
        self._modifier_id = None
        self._internal_config:bool = aj_config is None
        self._aj_config:AjConfig = aj_config or AjConfig()
        self._db_engine:aio_sa.AsyncEngine = None
        self._AsyncSessionMaker:aio_sa.async_sessionmaker = None   #pylint: disable=invalid-name   #variable is a class factory
        self._aio_session:aio_sa.async_sessionmaker[aio_sa.AsyncSession] = None

    async def __aenter__(self):
        if self._internal_config:
            self._aj_config.__enter__()

        # Connect to MariaDB Platform
        self._db_engine = aio_sa.create_async_engine("mysql+aiomysql://" + self._aj_config.db_connection_string,
                                                    echo=self._aj_config.db_echo)

        # aio_sa.async_sessionmaker: a factory for new AsyncSession objects
        # expire_on_commit - don't expire objects after transaction commit
        self._AsyncSessionMaker = aio_sa.async_sessionmaker(bind = self._db_engine, expire_on_commit=False)
        self._aio_session = self._AsyncSessionMaker()

        # If modifier discord name is provided, retrieve user id from it
        if self._modifier_discord:
            query = sa.select(db_t.Member.id).where(db_t.Member.discord == self._modifier_discord)
            member_id = (await self._aio_session.scalars(query)).one_or_none()
            if member_id is None:
                raise AjDbException(f"le pseudo discord '{self._modifier_discord}' n'est associé à aucun membre de l'asso.")
            self._modifier_id = member_id

        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        # Commit & close session, flushing all pending changes
        try:
            await self._aio_session.commit()
        except Exception:
            await self._aio_session.rollback()
            raise
        finally:
            await self._aio_session.close()
        self._aio_session = None
        # Close and clean-up pooled connections
        await self._db_engine.dispose()
        self._AsyncSessionMaker = None
        if self._internal_config:
            self._aj_config.__exit__(exc_type, exc_value, traceback)

    # session operation overrides
    # ===========================
    #TODO see how we can detect when update when commiting an update query
    #TODO see how we can detect when a child item is added during an item update (eg adding new address to an existing member), so we can update self._modifier_id
    def add(self, arg):
        """
            replace _aio.session.add
        """
        if not self._modifier_id:
            raise AjDbException("Cannot add without a modifier ID")

        if isinstance(arg, db_t.LogMixin):
            arg.log_author_id = self._modifier_id

        self._aio_session.add(arg)

    def add_all(self, argl:list):
        """
            replace _aio.session.add
        """
        if not self._modifier_id:
            raise AjDbException("Cannot add without a modifier ID")

        for arg in argl:
            if isinstance(arg, db_t.LogMixin):
                arg.log_author_id = self._modifier_id

        self._aio_session.add_all(argl)

    # DB Management
    # =============
    async def drop_create_schema(self):
        """ recreate database schema
        """
        if self._aj_config.db_creds['user'] not in  ['root', 'ajadmin']:
            raise AjDbException(f"L'utilisateur {self._aj_config.db_creds['user']} ne peut pas recréer la base de donnée !")
        # create all tables
        async with self._db_engine.begin() as conn:
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
        return (await self._aio_session.scalars(query)).all()


    @_async_cached
    async def query_seasons(self, lazyload:bool=True) -> list[db_t.Season]:
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

        return (await self._aio_session.scalars(query)).all()

    @_async_cached
    async def query_asso_roles(self, lazyload:bool=True) -> list[db_t.AssoRole]:
        ''' retrieve list of asso roles
            @args
                lazyload = if True, use lazyload for roles and members

            @return
                [all found roles]
        '''
        query = sa.select(db_t.AssoRole)
        if lazyload:
            query = query.options(orm.lazyload(db_t.AssoRole.discord_roles), orm.lazyload(db_t.AssoRole.member_asso_role_associations).lazyload(db_t.MemberAssoRole.member))
        else:
            query = query.options(orm.selectinload(db_t.AssoRole.discord_roles), orm.selectinload(db_t.AssoRole.member_asso_role_associations).selectinload(db_t.MemberAssoRole.member))

        return (await self._aio_session.scalars(query)).all()


    # Members
    # -------
    async def query_members(self,
                     lookup_val = None,
                     match_crit = 50,
                     break_if_multi_perfect_match = True,) -> list[db_t.Member]:
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
                raise AjDbException(f"Le champ de recherche {lookup_val} n'est pas reconnu comme de type discord") from e

        # check if lookup_val is an integer (member ID)
        elif isinstance(lookup_val, int):
            query = sa.select(db_t.Member).where(db_t.Member.id == lookup_val)

        elif isinstance(lookup_val, str):
            query = sa.select(db_t.Member).where(db_t.Member.credential)

        else:
            raise AjDbException(f"Le champ de recherche doit être de type 'discord', 'int' or 'str', pas '{type(lookup_val)}'")


        matched_members = (await self._aio_session.scalars(query)).all()

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


    async def query_members_per_season_presence(self, season_name = None, subscriber_only = False) -> list[db_t.Member]:
        ''' retrieve list of members having participated in season
            @args
                season_name     [Optional] If empty, use current season
                subscriber_only [Optional] If True return only people that have subscribed

            @return
                [all found members with number of presence]
        '''

        query = sa.select(db_t.Member)
        if subscriber_only:
            query = query.join(db_t.Member.memberships)
        else:
            query = query.join(db_t.Member.event_member_associations).join(db_t.MemberEvent.event)

        if season_name:
            where = db_t.Season.name == season_name
        else:
            where = db_t.Season.is_current_season

        query = query.join(db_t.Season)\
                     .where(where)\
                     .group_by(db_t.Member)

        members = (await self._aio_session.scalars(query)).all()
        return members

    async def query_members_per_event_presence(self, event_id) -> list[db_t.Member]:
        ''' retrieve list of members having participated to an event
            @args
                event_id
            @return
                [all found members with number of presence]
        '''
        query = sa.select(db_t.Member)\
                  .join(db_t.Member.event_member_associations)\
                  .where(db_t.MemberEvent.event_id == event_id)\
                  .group_by(db_t.Member)

        return (await self._aio_session.scalars(query)).all()

    async def query_discord_member(self, discord_member: discord.Member, must_exist=True) -> db_t.Member:
        ''' retrieve user from discord member, checking for its unicity and existence (if asked)
        '''
        members = await self.query_members(lookup_val=discord_member,
                                           match_crit = 100,
                                           break_if_multi_perfect_match = False)
        if not members:
            if must_exist:
                raise AjDbException(f"{discord_member} n'est pas associé à un membre de l'asso.")

            return None

        if len(members) > 1:
            raise AjDbException(f"{discord_member} est associé à plus d'un membre de l'asso: {','.join(u.id for u in members)}.")

        return members[0]

    async def query_member_sign_sheet(self, sign_sheet_file):
        """ Create a sign sheet PDF file for all members with presence in current season
            sign_sheet_file: file-like object
        """
        members = await self.query_members_per_season_presence()
        free_venues = self._aj_config.asso_free_presence

        # sort alphabetically per last name / first name
        members.sort(key=lambda x: x.credential)

        # use Matplotlib to write to a PDF, creating a figure with only the data table showing up
        inch_to_cm = 2.54
        fig, ax = plt.subplots(figsize=(21/inch_to_cm, 29.7/inch_to_cm))  # A4 size in inches

        ax.axis('off')
        input_dic = [{'ID': f"{member.id:{FormatTypes.FULLSIMPLE}}",
                      'Nom': f"{member.credential:{FormatTypes.FULLSIMPLE}}",
                      '#': "" if member.is_subscriber else f"{'>' if member.season_presence_count() >= free_venues else ''}{member.season_presence_count()}",
                      'Signature': '',
                     } for member in members]

        input_list = [list(d.values()) for d in input_dic]
        input_columns = list(input_dic[0].keys())
        input_columns_width = [0.1, 0.3, 0.1, 0.5] # Need adjust if changing list of columns, total should always be 1

        row_per_page = 20
        table_height_scale = 2.7  # Need adjust if changing mbr_per_page

        # add empty rows to have full pages + one full blank page
        n_empty_rows = row_per_page - (((len(input_list) - 1) % row_per_page) + 1)
        n_empty_rows += row_per_page
        input_list += [['']*len(input_columns)]*n_empty_rows

        # Create the PDF and write the table to it, splited per page
        with PdfPages(sign_sheet_file) as signsheet_file:
            for sub_input_list in divide_list(input_list, row_per_page):
                _the_table = ax.table(
                    cellText=sub_input_list,
                    cellLoc='center',
                    colLabels=input_columns,
                    colWidths=input_columns_width,
                    loc='center',
                )
                _the_table.scale(1, table_height_scale)

                signsheet_file.savefig(fig)

    async def query_member_emails(self, last_participation_duration:Optional[timedelta]=None) -> list[db_t.Email]:
        """ return list of member emails

            last_participation_duration: if None, emails of current season subscribers
                                         if not none: emails of any people present in the last last_presence_delta
        """
        members:list[db_t.Member] = await self.query_table_content(db_t.Member, refresh_cache=True)   #pylint: disable=unexpected-keyword-arg # decorator argument

        return [m.email_principal.email for m in members if     m.email_principal
                                                            and (   m.is_subscriber
                                                                or (    last_participation_duration is not None
                                                                    and m.last_presence
                                                                    and m.last_presence >= (datetime.now().date() - last_participation_duration)
                                                                    )
                                                                )]


    async def add_update_member(self,
                                member_id = None,
                                last_name:Optional[str]=None,
                                first_name:Optional[str]=None,
                                birthdate:Optional[date]=None,
                                discord_name:Optional[str]=None) -> db_t.Member:
        """ add or update an event
        """

        if not member_id:
            db_member = db_t.Member()
            db_member.credential = db_t.Credential()
            self.add(db_member)
        else:
            query = sa.select(db_t.Member).where(db_t.Member.id == member_id)
            db_member = (await self._aio_session.scalars(query)).one_or_none()

        db_member.credential.first_name = first_name
        db_member.credential.last_name = last_name
        db_member.credential.birthdate = birthdate
        db_member.credential.log_author_id = self._modifier_id
        db_member.discord = discord_name
        db_member.log_author_id = self._modifier_id

        await self._aio_session.commit()
        await self._aio_session.refresh(db_member)

        return db_member

    # Events
    # -------
    @_async_cached
    async def query_events(self, event_str:Optional[str] = None, lazyload:bool=True) -> list[db_t.Event]:
        ''' retrieve all events or with a given name
            @args
                event_str = Optional. if empty, return all events
                lazyload = if True, use lazyload for members

            @return
                [all found events]
        '''
        query = sa.select(db_t.Event)
        if lazyload:
            query = query.options(orm.lazyload(db_t.Event.member_event_associations).lazyload(db_t.MemberEvent.member))
        else:
            query = query.options(orm.selectinload(db_t.Event.member_event_associations).selectinload(db_t.MemberEvent.member))

        events = (await self._aio_session.scalars(query)).all()
        if event_str:
            events = [e for e in events if str(e) == event_str]

        return events


    async def query_events_per_season(self, season_name:Optional[str] = None, lazyload:bool=True) -> list[db_t.Event]:
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
            query = query.options(orm.lazyload(db_t.Event.member_event_associations).lazyload(db_t.MemberEvent.member))
        else:
            query = query.options(orm.selectinload(db_t.Event.member_event_associations).selectinload(db_t.MemberEvent.member))

        events = (await self._aio_session.scalars(query)).all()

        return events


    async def add_update_event(self,
                               event_id = None,
                               event_date:Optional[date]=None,
                               event_name:Optional[str]=None,
                               participant_ids:Optional[list[int]]=None,) -> db_t.Event:
        """ add or update an event
        """
        participant_ids = list(set(participant_ids))    # remove any duplicate
        query = sa.select(sa.func.max(db_t.Member.id))
        last_valid_member_id = (await self._aio_session.scalars(query)).one_or_none()
        unkown_participant_ids = [i for i in participant_ids if i > last_valid_member_id]

        if unkown_participant_ids:
            raise AjDbException(f"ID asso inconnu(s): {', '.join(str(i) for i in unkown_participant_ids)}")

        # create or get event
        if not event_id:
            if not event_date:
                raise AjDbException("Date du nouvel évènement manquante.")
            db_event = db_t.Event(date=event_date)
            seasons:list[db_t.Season] = await self.query_table_content(db_t.Season, orm.lazyload(db_t.Season.events), orm.lazyload(db_t.Season.memberships))
            [db_event.season] = [s for s in seasons if db_event.date >= s.start and db_event.date <= s.end]
            self.add(db_event)

            # Need to create event first to have its id, before being able to add participants
            # This will also raise an error if event at same date already exists
            await self._aio_session.commit()
            await self._aio_session.refresh(db_event)
        else:
            if event_date:
                raise AjDbException("Evènement existe et date fournie. Ce n'est pas permis.")
            query = sa.select(db_t.Event).where(db_t.Event.id == event_id)
            db_event = (await self._aio_session.scalars(query)).one_or_none()
            if not db_event:
                raise AjDbException(f"Evènement inconnu: {event_id}")

        # set name
        db_event.name = event_name

        db_event.log_author_id = self._modifier_id

        # delete / add participants
        for mbr_evt in db_event.member_event_associations:
            if mbr_evt.member_id not in participant_ids:
                await self._aio_session.delete(mbr_evt)

        existing_participant_ids = [mbr.id for mbr in db_event.members]
        self.add_all([db_t.MemberEvent(member_id = mbr_id, event_id=db_event.id, presence = True)
                      for mbr_id in participant_ids
                      if mbr_id not in existing_participant_ids])

        await self._aio_session.commit()
        await self._aio_session.refresh(db_event)

        return db_event



if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
