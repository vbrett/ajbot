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

        for qr in query_result:
            print(f'{qr:{FormatTypes.RESTRICTED}}', '-----', f'{qr:{FormatTypes.FULLSIMPLE}}')
        print(len(query_result))
        print('-------------------')

        query = sa.select(ajdb.Events).filter(ajdb.Events.is_in_current_season)
        async with aj_db.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)

        matched_events = query_result.scalars().all()
        for e in matched_events:
            print(e)
        print(len(matched_events))
        print('-------------------')

        query = sa.select(ajdb.Members).filter(ajdb.Members.is_current_subscriber)
        async with aj_db.AsyncSessionMaker() as session:
            async with session.begin():
                query_result = await session.execute(query)
        matched_members = query_result.scalars().all()
        for e in matched_members:
            print(e)
        print(len(matched_members))
        print('-------------------')

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_read_db()))
