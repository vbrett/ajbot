"""
Library for support package exceptions
"""

class SecretException(Exception):
    """Exception related to secret management"""

class OtherException(Exception):
    """General exception for Support package"""


if __name__ == '__main__':
    raise OtherException('This module should not be called directly.')
