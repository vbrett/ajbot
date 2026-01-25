"""
approval tests
"""
from pathlib import Path
import pytest

from tests.support import pre_condition, TEST_PATH, TEST_MIGRATE_FILE


from ajbot._internal.exceptions import OtherException
from ajbot.migrate import _async_main as migrate


@pytest.mark.asyncio
async def test_migrate():
    """
    Unit test for migrating a db
    """
    pre_condition()
    await migrate(ajdb_xls_file=Path(TEST_PATH) / TEST_MIGRATE_FILE)

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
