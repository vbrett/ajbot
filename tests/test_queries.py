"""
approval tests - queries
"""
from typing import Optional

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
