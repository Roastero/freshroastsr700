# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import time
import serial
import threading

from freshroastsr700 import utils
from freshroastsr700 import exceptions


class freshroastsr700(object):
    """A class to interface with a freshroastsr700 coffee roaster."""
    def __init__(self, update_data_func=None, state_transition_func=None):
        """Create variables used to send in packets to the roaster. The update
        data function is called when a packet is opened. The state transistion 
        function is used by the timer thread to know what to do next. See wiki
        for more information on packet structure and fields."""
        self.update_data_func = update_data_func
        self.state_transition_func = state_transition_func 

        self._header = b'\xAA\xAA'
        self._temp_unit = b'\x61\x74'
        self._flags = b'\x63'
        self._current_state = b'\x02\x01'
        self._fan_speed = 1
        self._heat_setting = 0
        self._footer = b'\xAA\xFA'

        self.current_temp = 150
        self.time_remaining = 0
        self.total_time = 0

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
    def heat_setting(self):
        """A getter method for _heat_setting."""
        return self._heat_setting

    @heat_setting.setter
    def heat_setting(self, value):
        """Verifies that the heat setting is between 0 and 3."""
        if value not in range(0, 4):
            raise exceptions.RoasterValueError

        self._heat_setting = value

    def connect(self):
        """Creates a serial object, sends initialization packet, and starts
        main communications loop to the roaster."""
        port = utils.find_device('1A86:5523')
        self._ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1.5,
            timeout=.25,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False)

        self._header = b'\xAA\x55'
        self._current_state = b'\x00\x00'
        s = self.generate_packet()
        self._ser.write(s)
        self._header = b'\xAA\xAA'
        self._current_state = b'\x02\x01'

        self._cont = True
        self.comm_thread = threading.Thread(target=self.comm)
        self.comm_thread.start()
        self.time_thread = threading.Thread(target=self.timer)
        self.time_thread.start()

    def disconnect(self):
        """Stops the communication loop to the roaster. Note that this will not
        actually stop the roaster itself, but will allow the program to exit
        cleanly."""
        self._cont = False

    def comm(self):
        """Main communications loop to the roaster. If the packet is not 14
        bytes exactly, the packet will not be opened. If an update data
        function is available, it will be called when the packet is opened."""
        while(self._cont):
            if(self._ser.is_open != True):
                break;

            r = self._ser.readline()
            if len(r) == 14:
                self.open_packet(r)
                if(self.update_data_func is not None):
                    self.update_data_func(self)

            s = self.generate_packet()
            self._ser.write(s)

            time.sleep(.25)

        self._ser.close()

    def timer(self):
        """Timer loop used to keep track of the time while roasting or
        cooling. If the time remaining reaches zero, the roaster will call the
        supplied state transistion function or the roaster will be set to
        the idle state."""
        while(self._cont):
            state = self.get_roaster_state()
            if(state == 'roasting' or state == 'cooling'):
                time.sleep(1)
                self.total_time += 1
                if(self.time_remaining > 0):
                    self.time_remaining -= 1
                else:
                    if(self.state_transition_func is not None):
                        self.state_transition_func(self, state)
                    else:
                        self.idle()

    def get_roaster_state(self):
        """Returns a string based upon the current state of the roaster. Will
        raise an exception if the state is unknown."""
        if(self._current_state == b'\x04\x02'):
            return 'roasting'
        elif(self._current_state == b'\x04\x04'):
            return 'cooling'
        elif(self._current_state == b'\x02\x01'):
            return 'idle'
        elif(self._current_state == b'\x08\x01'):
            return 'sleeping'

        raise exceptions.RoasterStateError

    def generate_packet(self):
        """Generates a packet based upon the current class variables. Note that
        current temperature is not sent, as the original application sent zeros
        to the roaster for the current temperature."""
        roaster_time = utils.seconds_to_float(self.time_remaining)
        packet = (
            self._header +
            self._temp_unit +
            self._flags +
            self._current_state +
            self.fan_speed.to_bytes(1, byteorder='big') +
            int(float(roaster_time * 10)).to_bytes(1, byteorder='big') +
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
        self._current_state = b'\x02\x01'

    def roast(self):
        """Sets the current state of the roaster to roast and begins
        roasting."""
        self._current_state = b'\x04\x02'

    def cool(self):
        """Sets the current state of the roaster to cool. The roaster expects
        that cool will be run after roast, and will not work as expected if ran
        before."""
        self._current_state = b'\x04\x04'

    def sleep(self):
        """Sets the current state of the roaster to sleep. Different than idle
        in that this will set double dashes on the roaster display rather than
        digits."""
        self._current_state = b'\x08\x01'
