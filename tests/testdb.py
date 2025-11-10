""" test deployment of a MariaDB instance
"""
import sys
import asyncio

import sqlalchemy as sa

from ajbot._internal import ajdb
from ajbot._internal.ajdb import AjDb

async def _read_db():
    """ main function - async version
    """
    async with AjDb() as aj_db:
        async with aj_db.AsyncSessionMaker() as session:
            async with session.begin():
                query = sa.select(ajdb.Members) #.options(orm.selectinload(ajdb.Members.credential))
                query_result = await session.execute(query)
                for qr in query_result.scalars():
                    print(f'{qr:simple}', '-----', f'{qr:full}')

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_read_db()))
