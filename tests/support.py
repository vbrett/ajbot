"""
Support function to perform tests
"""
from typing import Callable, Optional, Any, Sequence
from itertools import product
from pathlib import Path

import approvaltests

from ajbot._internal.exceptions import OtherException
import ajbot._internal.config

REPORT_EOL = '\n'
TEST_PATH = Path('tests/db_test')
TEST_ENV_FILE = 'test.env'
TEST_MIGRATE_FILE = 'db_test.xlsx'



VariationForEachParameter = Sequence[Sequence[Any]]
CombinationsOfParameters = Sequence[Sequence[Any]]

async def async_verify_all_combinations_with_labeled_input(
    function_under_test: Callable,
    *,  # enforce keyword arguments - https://www.python.org/dev/peps/pep-3102/
    _options: Optional[Any] = None, # not used in this implementation, only kept for compatibility with original function
    **kwargs: Any,
) -> None:
    """
        Replace approvaltests.verify_all_combinations_with_labeled_input which does not support awaitable function
    """
    labels = list(kwargs.keys())
    input_arguments: VariationForEachParameter = list(kwargs.values()) # [v for k,v in kwargs.values()]

    def formatter(inputs: Sequence[Any], output: Any) -> str:
        labeled_inputs = ", ".join(
            [f"{label}: {input}" for label, input in zip(labels, inputs)]
        )
        return f"({labeled_inputs}) =>{REPORT_EOL}{output}{REPORT_EOL}{REPORT_EOL}"

    parameter_combinations: CombinationsOfParameters = product(*input_arguments)

    approval_strings = []
    for args in parameter_combinations:
        try:
            result = await function_under_test(*args)
        except BaseException as exception:      # pylint: disable=broad-exception-caught    # catching all exeception is done on purpose for test
            result = exception
        approval_strings.append(formatter(args, result))

    approvaltests.verify("".join(approval_strings))


def get_printable_ajdb_objects(ajdb_objects, str_format, merge=True):
    """ transform list of db objects as printed list
    """
    output = [f"{o:{str_format}}" for o in ajdb_objects]

    if merge:
        return REPORT_EOL.join(output)

    return output

def pre_condition():
    """
    prepare test environement
    """
    ajbot._internal.config._AJ_CONFIG_PATH = TEST_PATH  #pylint: disable=protected-access #override default ajconfif path & file for test
    ajbot._internal.config._AJ_CONFIG_FILE = TEST_ENV_FILE  #pylint: disable=protected-access #override default ajconfif path & file for test




if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
