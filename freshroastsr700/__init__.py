# -*- coding: utf-8 -*-
# Roastero, released under GPLv3


class freshroastsr700(object):
    """A class to interface with a freshroastsr700 coffee roaster."""
    def __init__(self):
        """Create variables used to send in packets to the roaster. See wiki
        for more information on packet structure and fields."""
        # Variables that are not meant to be used outside of the class.
        self._header = b'\xAA\xAA'
        self._temp_unit = b'\x61\x74'
        self._flags = b'\x63'
        self._control = b'\x02\x01'
        self._footer = b'\xAA\xFA'

        # Variables that are meant to be used outside of the class.
        self.fan_speed = 0
        self.heat_setting = 0
        self.time_remaining = 0.0
        self.current_temp = 150
