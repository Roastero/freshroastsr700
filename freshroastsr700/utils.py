# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Mark Spicer
# Made available under the MIT license.

import re
from serial.tools import list_ports

from freshroastsr700 import exceptions


def frange(start, stop, step, precision):
    """A generator that will generate a range of floats."""
    value = start
    while round(value, precision) < stop:
        yield round(value, precision)
        value += step


def find_device(vidpid):
    """Finds a connected device with the given VID:PID. Returns the serial
    port url."""
    for port in list_ports.comports():
        if re.search(vidpid, port[2], flags=re.IGNORECASE):
            return port[0]

    raise exceptions.RoasterLookupError


def seconds_to_float(time_in_seconds):
    """Converts seconds to float rounded to one digit. Will cap the float at
    9.9 or 594 seconds."""
    if(time_in_seconds <= 594):
        return round((float(time_in_seconds) / 60.0), 1)

    return 9.9
