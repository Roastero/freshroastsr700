# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

from freshroastsr700 import utils
from freshroastsr700 import exceptions


class freshroastsr700(object):
    """A class to interface with a freshroastsr700 coffee roaster."""
    def __init__(self):
        """Create variables used to send in packets to the roaster. See wiki
        for more information on packet structure and fields."""
        self._header = b'\xAA\xAA'
        self._temp_unit = b'\x61\x74'
        self._flags = b'\x63'
        self._current_state = b'\x02\x01'
        self._fan_speed = 1
        self._time_remaining = 0.0
        self._heat_setting = 0
        self._current_temp = 150
        self._footer = b'\xAA\xFA'

    @property
    def fan_speed(self):
        """A getter method for _fan_speed."""
        return self._fan_speed

    @fan_speed.setter
    def fan_speed(self, value):
        """Verifies the value is between 1 and 9 inclusively."""
        if value not in range(1, 10):
            raise exceptions.RoasterValueError

        self._fan_speed = value

    @property
    def time_remaining(self):
        """A getter method for _time_remaining."""
        return self._time_remaining

    @time_remaining.setter
    def time_remaining(self, value):
        """Verifies that the time remaining is between 0.0 and 9.9."""
        if value not in utils.frange(0.0, 10, 0.1, 1):
            raise exceptions.RoasterValueError

        self._time_remaining = value

    @property
    def heat_setting(self):
        """A getter method for _heat_setting."""
        return self._heat_setting

    @heat_setting.setter
    def heat_setting(self, value):
        """Verifies that the heat setting is between 0 and 3."""
        if value not in range(0, 4):
            raise exceptions.RoasterValueError

        self._heat_setting = value

    def generate_packet(self):
        """Generates a packet based upon the current class variables. Note that
        current temperature is not sent, as the original application sent zeros
        to the roaster for the current temperature."""
        packet = (
            self._header +
            self._temp_unit +
            self._flags +
            self._current_state +
            self.fan_speed.to_bytes(1, byteorder='big') +
            int(float(self.time_remaining * 10)).to_bytes(1, byteorder='big') +
            self.heat_setting.to_bytes(1, byteorder='big') +
            b'\x00\x00' +
            self._footer)

        return packet

    def open_packet(self, packet):
        """Opens a packet received from the roaster and sets the temperature
        accordingly. Since the roaster sends 65280 if the temperature is not
        above 150, this method will set 65280 at 150."""
        if(bytes(packet[10:-2]) == (b'\xff\x00')):
            self.current_temp = 150
            return

        self.current_temp = int.from_bytes(
            bytes(packet[10:-2]), byteorder='big')

    def idle(self):
        """Sets the current state of the roaster to idle."""
        self.current_state = b'\x02\x01'

    def roast(self):
        """Sets the current state of the roaster to roast and begins
        roasting."""
        self.current_state = b'\x04\x02'

    def cool(self):
        """Sets the current state of the roaster to cool. The roaster expects
        that cool will be run after roast, and will not work as expected if ran
        before."""
        self.current_state = b'\x04\x04'

    def sleep(self):
        """Sets the current state of the roaster to sleep. Different than idle
        in that this will set double dashes on the roaster display rather than
        digits."""
        self.current_state = b'\x08\x01'
