# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Mark Spicer
# Made available under the MIT license.


class RoasterError(Exception):
    """A base error for freshroastsr700 errors."""


class RoasterValueError(RoasterError):
    """Raised when a class variable assigned is out of the range of acceptable
    values."""


class RoasterLookupError(RoasterError):
    """Raised when a device is not able to be found from the connected
    devices."""


class RoasterStateError(RoasterError):
    """Raised when the current state of the roaster is not a known roaster
    state."""
