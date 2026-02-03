""" test deployment of a DB instance
"""
import sys
import asyncio
from typing import cast
from functools import wraps

import sqlalchemy as sa

from ajbot._internal.ajdb import AjDb, tables as db_t
from ajbot._internal.config import FormatTypes


def _test_case(func):
    """ Decorator to test functions
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        print()
        print()
        return result
    return wrapper



@_test_case
async def _season_events(aj_db_session):
    query = sa.select(db_t.Event).where(db_t.Event.is_in_current_season)
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

@_test_case
async def _principal_address(aj_db_session):
    query = sa.select(db_t.MemberAddress).where(db_t.Member.address_principal is not None)
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


@_test_case
async def _test_query(aj_db_session):
    season_name = "2025-2026"
                # .with_only_columns(db_t.Member.id, db_t.Member.credential, sa.func.count(db_t.Member.memberships))\
    query = sa.select(db_t.Member)\
                .join(db_t.Member.event_member_associations)\
                .join(db_t.MemberEvent.event)\
                .join(db_t.Event.season)\
                .where(db_t.Season.name == season_name)\
                .group_by(db_t.Member)
    async with aj_db_session.AsyncSessionMaker() as session:
        async with session.begin():
            query_result = await session.execute(query)
    matched_items = query_result.scalars().all()
    matched_items.sort(key=lambda x: cast(db_t.Member, x).credential, reverse=False)
    for m in matched_items:
        presence = len([event for event in cast(db_t.Member, m).events
                        if event.season.name == season_name])
        print(f"{m:{FormatTypes.FULL}} - {presence} présence(s)")
    print(len(matched_items), 'item(s)')



async def _test_stuff():
    async with AjDb() as aj_db:

        await _season_events(aj_db)
        await _principal_address(aj_db)

        await _test_query(aj_db)





##################################################################
##################################################################
##################################################################
async def _main():
    """ main function - async version
    """

    # Original test
    await _test_stuff()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
