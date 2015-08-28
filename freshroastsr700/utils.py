# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

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
    current_comm_ports = list_ports.comports()

    for port in current_comm_ports:
        if re.search(vidpid, port[2], flags=re.IGNORECASE):
            return port[0]

    raise exceptions.RoasterLookupError
