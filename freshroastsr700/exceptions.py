# -*- coding: utf-8 -*-
# Roastero, released under GPLv3


class RoasterError(Exception):
    """A base error for freshroastsr700 errors."""


class RoasterValueError(RoasterError):
    """Raised when a class variable assigned is out of the range of acceptable
    values."""


class RoasterLookupError(RoasterError):
    """Raised when a device is not able to be found from the connected 
    devices."""
