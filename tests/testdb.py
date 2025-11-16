""" test deployment of a MariaDB instance
"""
import sys
import asyncio
import sqlalchemy as sa

from ajbot._internal import ajdb
from ajbot._internal.config import FormatTypes

async def _search_member(aj_db_session, lokkup_val):
    query_result = await aj_db_session.search_member(lokkup_val)
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
    query = sa.select(ajdb.Events).where(ajdb.Events.is_in_current_season)
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
    query = sa.select(ajdb.JCTMemberAddress).where(ajdb.Members.address_principal is not None)
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
                # .with_only_columns(ajdb.Members.id, ajdb.Members.credential, sa.func.count(ajdb.Members.memberships))\
    query = sa.select(ajdb.Members, ajdb.Events)\
                .join(ajdb.JCTEventMember)\
                .join(ajdb.Events)\
                .join(ajdb.Seasons)\
                .where(ajdb.Seasons.name == "2025-2026")\
                .select_from(ajdb.Members)
    async with aj_db_session.AsyncSessionMaker() as session:
        async with session.begin():
            query_result = await session.execute(query)
    matched_items = query_result.scalars().all()
    matched_items = list(set(matched_items))
    matched_items.sort(key=lambda x: x.credential, reverse=False)
    for e in matched_items:
        print(f'{e:{FormatTypes.FULLSIMPLE}} - {len(e.memberships)} cotisations(s)')
    print(len(matched_items), 'item(s)')



async def _main():
    """ main function - async version
    """
    async with ajdb.AjDb() as aj_db_session:

        # await _search_member(aj_db_session, 'vincent')
        # await _season_events(aj_db_session)
        # await _principal_address(aj_db_session)

        await _test_query(aj_db_session)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
