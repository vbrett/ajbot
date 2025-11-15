""" test deployment of a MariaDB instance
"""
import sys
import asyncio
import sqlalchemy as sa

from ajbot._internal import ajdb
from ajbot._internal.config import FormatTypes

async def _read_db():
    """ main function - async version
    """
    async with ajdb.AjDb() as aj_db:

        query_result = await aj_db.search_member('vincent')
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

        query = sa.select(ajdb.Events).filter(ajdb.Events.is_in_current_season)
        async with aj_db.AsyncSessionMaker() as session:
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

        query = sa.select(ajdb.JCTMemberAddress).where(ajdb.Members.address_principal is not None)
        async with aj_db.AsyncSessionMaker() as session:
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

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_read_db()))
