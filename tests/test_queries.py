"""
approval tests - queries
"""
import pytest

import sqlalchemy as sa

from ajbot._internal.ajdb import AjDb, tables as db_t
from ajbot._internal.config import AjConfig, FormatTypes

from tests.support import async_verify_all_combinations_with_labeled_input, get_printable_ajdb_objects, ExpectedExceptionDuringTest



async def _do_query_table_content(input_table, input_format):
    with AjConfig() as aj_config:
        async with AjDb(aj_config=aj_config) as aj_db:
            items = await aj_db.query_table_content(input_table)
            result = get_printable_ajdb_objects(ajdb_objects=items,
                                                str_format=input_format)

    return result

@pytest.mark.asyncio
async def test_query_table_content():
    """
    Unit test for aj_db.query_table_content
    """
    tables = [
              db_t.StreetType,
              db_t.ContributionType,
              db_t.AccountType,
              db_t.KnowFromSource,

              db_t.Season,

              db_t.AssoRole,
              db_t.DiscordRole,
              db_t.MemberAssoRole,
              db_t.AssoRoleDiscordRole,

              db_t.Member,
              db_t.Credential,
              db_t.Email,
              db_t.Phone,
              db_t.PostalAddress,
              db_t.MemberAddress,
              db_t.MemberEmail,
              db_t.MemberPhone,

              db_t.Membership,
              db_t.Event,
              db_t.MemberEvent,
             ]
    formats = [None,
               FormatTypes.RESTRICTED,
               FormatTypes.FULL,
               FormatTypes.DEBUG]

    await async_verify_all_combinations_with_labeled_input(_do_query_table_content,
                                                           input_table = tables,
                                                           input_format = formats)

async def _do_query_events(event:str, lazyload:bool):
    async with AjDb() as aj_db:
        items = await aj_db.query_events(event, lazyload=lazyload)
        try:
            result = get_printable_ajdb_objects(ajdb_objects=items,
                                                str_format=FormatTypes.FULL)
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
