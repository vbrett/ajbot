"""
approval tests
"""
from pathlib import Path

import pytest
import approvaltests

from tests.support import TEST_PATH, TEST_MIGRATE_FILE, REPORT_EOL

from ajbot._internal.exceptions import OtherException
from ajbot.migrate import migrate

@pytest.mark.asyncio
async def test_migrate():
    """
    Unit test for migrating a db
    """
    result = ''
    items = await migrate(ajdb_xls_file=Path(TEST_PATH) / TEST_MIGRATE_FILE)
    result = REPORT_EOL.join(f"{type(i)} {i.id}" for i in items)

    approvaltests.verify(result)

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
