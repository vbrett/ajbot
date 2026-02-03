"""
approval tests - queries
"""
from typing import Optional
import tempfile
from datetime import date, timedelta

import pytest
import approvaltests

import sqlalchemy as sa
from sqlalchemy import orm

from ajbot._internal.ajdb import AjDb, tables as db_t
from ajbot._internal.config import AjConfig, FormatTypes

from tests.support import async_verify_all_combinations_with_labeled_input, get_printable_ajdb_objects, ExpectedExceptionDuringTest


##########################
async def _do_query_table_content(args:tuple, input_format, refresh_cache):
    with AjConfig() as aj_config:
        async with AjDb(aj_config=aj_config) as aj_db:
            items = await aj_db.query_table_content(*args,
                                                    refresh_cache=refresh_cache)
            result = get_printable_ajdb_objects(ajdb_objects=items,
                                                str_format=input_format)

    return result

@pytest.mark.asyncio
async def test_query_table_content():
    """
    Unit test for aj_db.query_table_content
    """
    args = [
              (db_t.StreetType, ),
              (db_t.ContributionType,),
              (db_t.AccountType,),
              (db_t.KnowFromSource,),

              (db_t.Season,),

              (db_t.AssoRole,),
              (db_t.DiscordRole,),
              (db_t.MemberAssoRole,),
              (db_t.AssoRoleDiscordRole,),

              (db_t.Member,),
              (db_t.Credential,),
              (db_t.Email,),
              (db_t.Phone,),
              (db_t.PostalAddress,),
              (db_t.MemberAddress,),
              (db_t.MemberEmail,),
              (db_t.MemberPhone,),

              (db_t.Membership,),
              (db_t.Event,),
              (db_t.MemberEvent,),
             ]
    formats = [None,
               FormatTypes.RESTRICTED,
               FormatTypes.FULL,
               FormatTypes.DEBUG]

    refresh_cache = [True, False]

    await async_verify_all_combinations_with_labeled_input(_do_query_table_content,
                                                           args = args,
                                                           input_format = formats,
                                                           refresh_cache=refresh_cache,)


##########################
@pytest.mark.asyncio
async def test_query_table_content_with_options():
    """
    Unit test for aj_db.query_table_content
    """
    result = await _do_query_table_content((db_t.Season, orm.lazyload(db_t.Season.events), orm.lazyload(db_t.Season.memberships)),
                                           FormatTypes.DEBUG,
                                           True)
    approvaltests.verify(result)


##########################
async def _do_query_seasons(lazyload:bool):
    async with AjDb() as aj_db:
        items = await aj_db.query_seasons(lazyload=lazyload)
        result = get_printable_ajdb_objects(ajdb_objects=items,
                                            str_format=FormatTypes.DEBUG)
        return result

@pytest.mark.asyncio
async def test_query_seasons():
    """
    Unit test for aj_db.query_seasons
    """
    lazyloads = [False, True]
    await async_verify_all_combinations_with_labeled_input(_do_query_seasons,
                                                           lazyload = lazyloads)


##########################
async def _do_query_asso_roles(lazyload:bool):
    async with AjDb() as aj_db:
        items = await aj_db.query_asso_roles(lazyload=lazyload)
        result = get_printable_ajdb_objects(ajdb_objects=items,
                                            str_format=FormatTypes.DEBUG)
        return result

@pytest.mark.asyncio
async def test_query_asso_roles():
    """
    Unit test for aj_db.query_asso_roles
    """
    lazyloads = [False, True]
    await async_verify_all_combinations_with_labeled_input(_do_query_asso_roles,
                                                           lazyload = lazyloads)


##########################
async def _do_query_events(event:str, lazyload:bool):
    async with AjDb() as aj_db:
        items = await aj_db.query_events(event, lazyload=lazyload)
        try:
            result = get_printable_ajdb_objects(ajdb_objects=items,
                                                str_format=FormatTypes.DEBUG)
        except sa.exc.StatementError as e:
            if lazyload:
                raise ExpectedExceptionDuringTest(f"{e.__class__.__name__}: Cannot get printable items. This is excepted since we're lazy loading data") from e
            raise e
        return result

@pytest.mark.asyncio
async def test_query_events():
    """
    Unit test for aj_db.query_events
    """
    events = [
            None,
            "Jan 10 2025 - Epiphanie 2025",
            ]
    lazyloads = [False, True]

    await async_verify_all_combinations_with_labeled_input(_do_query_events,
                                                           event = events,
                                                           lazyload = lazyloads)


##########################
async def _do_query_events_per_season(season:str, lazyload:bool):
    async with AjDb() as aj_db:
        items = await aj_db.query_events_per_season(season, lazyload=lazyload)
        try:
            result = get_printable_ajdb_objects(ajdb_objects=items,
                                                str_format=FormatTypes.DEBUG)
        except sa.exc.StatementError as e:
            if lazyload:
                raise ExpectedExceptionDuringTest(f"{e.__class__.__name__}: Cannot get printable items. This is excepted since we're lazy loading data") from e
            raise e
        return result

@pytest.mark.asyncio
async def test_query_events_per_season():
    """
    Unit test for aj_db.query_events_per_season
    """
    seasons = [
            None,
            "2020-2021",
            "2024-2025",
            "2025-2026",
            ]
    lazyloads = [False, True]

    await async_verify_all_combinations_with_labeled_input(_do_query_events_per_season,
                                                           season = seasons,
                                                           lazyload = lazyloads)


##########################
async def _do_add_update_event(event_id,
                               modifier_discord:Optional[str],
                               event_date:Optional[date],
                               event_name:Optional[str],
                               participant_ids:Optional[list[int]]):
    async with AjDb(modifier_discord=modifier_discord) as aj_db:
        items = await aj_db.add_update_event(event_id=event_id,
                                             event_date=event_date,
                                             event_name=event_name,
                                             participant_ids=participant_ids)
        result = get_printable_ajdb_objects(ajdb_objects=items,
                                            str_format=FormatTypes.DEBUG)
        return result

@pytest.mark.asyncio
async def test_add_update_event():
    """
    Unit test for aj_db.add_update_event
    """
    modifier_discords = [None, "user1", "vbrett"]
    event_ids = [
            None,
            # 1,
            # 88,
            # 250
            ]
    event_dates = [
            None,
            date(2025, 12, 31),
            # date(2026, 1, 18),
            ]
    event_names = [
            None,
            "Nouvel An 2026",
            # "bubou",
            ]
    participant_ids = [
            None,
            [],
            [1,2,3],
            # [10,20,30,40,50],
            # [36,151,14],
            ]

    await async_verify_all_combinations_with_labeled_input(_do_add_update_event,
                                                           modifier_discord=modifier_discords,
                                                           event_id=event_ids,
                                                           event_date=event_dates,
                                                           event_name=event_names,
                                                           participant_ids=participant_ids)

##########################
async def _do_query_members(lookup_val:Optional[str], match_crit, break_if_multi_perfect_match:bool):
    async with AjDb() as aj_db:
        items = await aj_db.query_members(lookup_val = lookup_val,
                                          match_crit = match_crit,
                                          break_if_multi_perfect_match = break_if_multi_perfect_match)
        result = get_printable_ajdb_objects(ajdb_objects=items,
                                            str_format=FormatTypes.DEBUG)
        return result

@pytest.mark.asyncio
async def test_query_members():
    """
    Unit test for aj_db.query_members
    """
    lookup_vals = [
                   None,
                   1,
                   2,
                   50,
                   "abc",
                   "Bon",
                   "Jean",
                   "Julie",
                   "Bon Jean",
                  ]
    match_crits = [0, 1, 25, 50, 60, 75, 80, 90, 99, 100]
    break_if_multi_perfect_matchs = [False, True]

    await async_verify_all_combinations_with_labeled_input(_do_query_members,
                                                           lookup_val = lookup_vals,
                                                           match_crit = match_crits,
                                                           break_if_multi_perfect_match = break_if_multi_perfect_matchs
                                                          )


##########################
async def _do_query_members_per_season_presence(season_name, subscriber_only):
    async with AjDb() as aj_db:
        items = await aj_db.query_members_per_season_presence(season_name = season_name, subscriber_only = subscriber_only)
        result = get_printable_ajdb_objects(ajdb_objects=items,
                                            str_format=FormatTypes.DEBUG)
        return result

@pytest.mark.asyncio
async def test_query_members_per_season_presence():
    """
    Unit test for aj_db.query_members_per_season_presence
    """
    season_names = [
                    None,
                    "Season Non Existent",
                    "2023-2024",
                   ]
    subscriber_onlys = [False, True]
    await async_verify_all_combinations_with_labeled_input(_do_query_members_per_season_presence,
                                                           season_name = season_names,
                                                           subscriber_only = subscriber_onlys)


##########################
async def _do_query_members_per_event_presence(event_id):
    async with AjDb() as aj_db:
        items = await aj_db.query_members_per_event_presence(event_id = event_id)
        result = get_printable_ajdb_objects(ajdb_objects=items,
                                            str_format=FormatTypes.DEBUG)
        return result

@pytest.mark.asyncio
async def test_query_members_per_event_presence():
    """
    Unit test for aj_db.query_members_per_event_presence
    """
    event_ids = [1,
                 20,
                 90,
                 9999,
                ]
    await async_verify_all_combinations_with_labeled_input(_do_query_members_per_event_presence,
                                                           event_id = event_ids)


##########################
@pytest.mark.asyncio
async def test_query_member_sign_sheet():
    """
    Unit test for aj_db.query_member_sign_sheet
    """
    async with AjDb() as aj_db:
        with tempfile.SpooledTemporaryFile(max_size=1024*1024, mode='w+b') as temp_file:
            await aj_db.query_member_sign_sheet(temp_file)

            # Set stream position back to file start to pass it to discord
            temp_file.seek(0)
            approvaltests.verify_binary(temp_file.read(), ".pdf")


##########################
async def _do_query_member_emails(last_participation_duration:int):
    async with AjDb() as aj_db:
        if last_participation_duration:
            last_participation_duration = timedelta(last_participation_duration)
        items = await aj_db.query_member_emails(last_participation_duration = last_participation_duration)
        result = get_printable_ajdb_objects(ajdb_objects=items,
                                            str_format=FormatTypes.DEBUG)
        return result

@pytest.mark.asyncio
async def test_query_member_emails():
    """
    Unit test for aj_db.query_member_emails
    """
    last_participation_durations = [None, 0, 10, 99, 9999]
    await async_verify_all_combinations_with_labeled_input(_do_query_member_emails,
                                                           last_participation_duration = last_participation_durations)
