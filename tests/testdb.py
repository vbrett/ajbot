""" test deployment of a MariaDB instance
"""
import sys
import asyncio

from ajbot._internal.ajdb import AjDb

async def _read_db():
    """ main function - async version
    """
    async with AjDb() as aj_db:
        query_result = await aj_db.search_member('vincent')

    for qr in query_result:
        print(f'{qr:restricted}', '-----', f'{qr:full}')


    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_read_db()))
