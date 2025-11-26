''' contains bot parameters, typically discord limitations
'''
from ajbot._internal.exceptions import OtherException

CONTENT_MAX_SIZE = 2000             # max size of a message
AUTOCOMPLETE_LIST_SIZE = 25         # max size of the autocomplete list
COMPONENT_MAX_NBR = 5               # max number of component in a view
COMPONENT_TEXT_SIZE = 4000          # max size of a text component
COMPONENT_SELECT_LIST_SIZE = 25     # max size of a select component list

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
