"""
Library for support package exceptions
"""

class CredsException(Exception):
    """ Exception related to credential management """

class AjDbException(Exception):
    """ Aj DB related exception """

class OtherException(Exception):
    """ General exception for Support package """

if __name__ == '__main__':
    raise OtherException('This module should not be called directly.')
