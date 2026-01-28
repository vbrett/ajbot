"""
approval tests - direct call of all module
"""

import runpy
import sys
from typing import Optional
from pathlib import Path

import approvaltests
from tests.support import TEST_PATH, TEST_MIGRATE_FILE


def _do_direct_call(modules:tuple[str, Optional[list[str]]]):
    module_name, args = modules
    if args is not None:
        sys.argv[1:] = args
    return runpy.run_module(module_name, run_name='__main__', alter_sys=True)


def test_direct_call():
    """
    Unit test for direct call of all module
    """
    modules = [
               ('ajbot.migrate', [Path(TEST_PATH) / 'elsewhere'/ TEST_MIGRATE_FILE]),
               ('ajbot._internal', None),
               ('ajbot._internal.config', None),
               ('ajbot._internal.exceptions', None),
               ('ajbot._internal.types', None),
               ('ajbot._internal.ajdb', None),
               ('ajbot._internal.ajdb.__init__', None),
               ('ajbot._internal.ajdb.tables', None),
               ('ajbot._internal.ajdb.tables.__init__', None),
               ('ajbot._internal.ajdb.tables.base', None),
              ]
    approvaltests.verify_all_combinations_with_labeled_input(_do_direct_call, modules=modules)
