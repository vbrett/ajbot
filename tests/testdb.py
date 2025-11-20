""" test deployment of a MariaDB instance
"""
import sys
import asyncio
from typing import cast

import sqlalchemy as sa

from ajbot._internal.ajdb import AjDb
from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal.config import FormatTypes

async def _search_member(aj_db_session, lookup_val):
    query_result = await aj_db_session.get_members(lookup_val)
    print('')
    print('')
    print('-------------------')
    for qr in query_result:
        print(f'{qr:{FormatTypes.RESTRICTED}}')
    print('-------------------')
    for qr in query_result:
        print(f'{qr:{FormatTypes.FULLSIMPLE}}')
    print('-------------------')
    for qr in query_result:
        print(f'{qr:{FormatTypes.FULLCOMPLETE}}')
        print('')
    print('-------------------')
    print('')
    print('')

async def _season_events(aj_db_session):
    query = sa.select(ajdb_t.Event).where(ajdb_t.Event.is_in_current_season)
    async with aj_db_session.AsyncSessionMaker() as session:
        async with session.begin():
            query_result = await session.execute(query)
    print('')
    print('')
    print('-------------------')
    matched_events = query_result.scalars().all()
    for e in matched_events:
        print(e)
    print(len(matched_events), 'évènement(s)')
    print('-------------------')

async def _principal_address(aj_db_session):
    query = sa.select(ajdb_t.MemberAddress).where(ajdb_t.Member.address_principal is not None)
    async with aj_db_session.AsyncSessionMaker() as session:
        async with session.begin():
            query_result = await session.execute(query)
    print('')
    print('')
    print('-------------------')
    matched_members = query_result.scalars().all()
    for e in matched_members:
        print(e.address)
    print(len(matched_members), 'membre(s) avec adresse principale')
    print('-------------------')


async def _test_query(aj_db_session):
    season_name = "2025-2026"
                # .with_only_columns(ajdb_t.Member.id, ajdb_t.Member.credential, sa.func.count(ajdb_t.Member.memberships))\
    query = sa.select(ajdb_t.Member)\
                .join(ajdb_t.MemberEvent)\
                .join(ajdb_t.Event)\
                .join(ajdb_t.Season)\
                .where(ajdb_t.Season.name == season_name)\
                .group_by(ajdb_t.Member)
    async with aj_db_session.AsyncSessionMaker() as session:
        async with session.begin():
            query_result = await session.execute(query)
    matched_items = query_result.scalars().all()
    matched_items.sort(key=lambda x: cast(ajdb_t.Member, x).credential, reverse=False)
    for m in matched_items:
        presence = len([member_event for member_event in cast(ajdb_t.Member, m).events
                        if member_event.event.season.name == season_name])
        print(f'{m:{FormatTypes.FULLSIMPLE}} - {presence} présence(s)')
    print(len(matched_items), 'item(s)')



async def _main():
    """ main function - async version
    """
    async with AjDb() as aj_db:

        # await _search_member(aj_db, 'vincent')
        # await _season_events(aj_db)
        # await _principal_address(aj_db)

        await _test_query(aj_db)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
