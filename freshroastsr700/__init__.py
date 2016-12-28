# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Mark Spicer
# Made available under the MIT license.

import time
import serial
import threading
import logging
import multiprocessing as mp
from multiprocessing import sharedctypes
import struct
import binascii

from freshroastsr700 import pid
from freshroastsr700 import utils
from freshroastsr700 import exceptions


class freshroastsr700(object):
    """A class to interface with a freshroastsr700 coffee roaster."""
    def __init__(self, update_data_func=None, state_transition_func=None,
                 thermostat=False):
        """Create variables used to send in packets to the roaster. The update
        data function is called when a packet is opened. The state transistion
        function is used by the timer thread to know what to do next. See wiki
        for more information on packet structure and fields."""
        self.update_data_func = update_data_func
        self.state_transition_func = state_transition_func

        self._header = sharedctypes.Array('c', b'\xAA\xAA')
        self._temp_unit = sharedctypes.Array('c', b'\x61\x74')
        self._flags = sharedctypes.Array('c', b'\x63')
        self._current_state = sharedctypes.Array('c', b'\x02\x01')
        self._footer = b'\xAA\xFA'

        self._fan_speed = sharedctypes.Value('i', 1)
        self._heat_setting = sharedctypes.Value('i', 0)
        self._target_temp = sharedctypes.Value('i', 150)
        self._current_temp = sharedctypes.Value('i', 150)
        self._time_remaining = sharedctypes.Value('i', 0)
        self._total_time = sharedctypes.Value('i', 0)

        self._cont = sharedctypes.Value('i', 1)

        if(thermostat is True):
            self.thermostat_process = mp.Process(target=self.thermostat)
            self.thermostat_process.start()

    @property
    def fan_speed(self):
        """A getter method for _fan_speed."""
        return self._fan_speed.value

    @fan_speed.setter
    def fan_speed(self, value):
        """Verifies the value is between 1 and 9 inclusively."""
        if value not in range(1, 10):
            raise exceptions.RoasterValueError

        self._fan_speed.value = value

    @property
    def heat_setting(self):
        """A getter method for _heat_setting."""
        return self._heat_setting.value

    @heat_setting.setter
    def heat_setting(self, value):
        """Verifies that the heat setting is between 0 and 3."""
        if value not in range(0, 4):
            raise exceptions.RoasterValueError

        self._heat_setting.value = value

    @property
    def target_temp(self):
        return self._target_temp.value

    @target_temp.setter
    def target_temp(self, value):
        if value not in range(150, 551):
            raise exceptions.RoasterValueError

        self._target_temp.value = value

    @property
    def current_temp(self):
        return self._current_temp.value

    @current_temp.setter
    def current_temp(self, value):
        if value not in range(150, 551):
            raise exceptions.RoasterValueError

        self._current_temp.value = value

    @property
    def time_remaining(self):
        return self._time_remaining.value

    @time_remaining.setter
    def time_remaining(self, value):
        self._time_remaining.value = value

    @property
    def total_time(self):
        return self._total_time.value

    @total_time.setter
    def total_time(self, value):
        self._total_time.value = value

    def connect(self):
        """Connects to the roaster and creates communication thread."""
        port = utils.find_device('1A86:5523')
        self._ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1.5,
            timeout=0.25,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False)

        self._initialize()

        self.comm_process = mp.Process(target=self.comm)
        self.comm_process.start()
        self.time_process = mp.Process(target=self.timer)
        self.time_process.start()

    def _initialize(self):
        """Sends the initialization packet to the roaster."""
        self._header.value = b'\xAA\x55'
        self._current_state.value = b'\x00\x00'
        s = self.generate_packet()
        self._ser.write(s)
        self._header.value = b'\xAA\xAA'
        self._current_state.value = b'\x02\x01'

        return self._read_existing_recipe()

    def _write_to_device(self):
        success = False
        try:
            packet = self.generate_packet()
            logging.debug('WR: ' + str(binascii.hexlify(packet)))
            self._ser.write(packet)
            success = True
        except serial.serialutil.SerialException:
            logging.error('caught serial exception writing')
            self._ser.close()
            self.auto_connect()
        return success

    def _read_from_device(self):
        r = []
        footer_reached = False
        while len(r) < 14 and footer_reached is False:
            r.append(self._ser.read(1))
            if len(r) >= 2 and b''.join(r)[-2:] == self._footer:
                footer_reached = True
        logging.debug('RD: ' + str(binascii.hexlify(b''.join(r))))
        return b''.join(r)

    def _read_existing_recipe(self):
        existing_recipe = []
        end_of_recipe = False
        while not end_of_recipe:
            bytes_waiting = self._ser.in_waiting
            if bytes_waiting < 14:
                # still need to write to device every .25sec it seems
                time.sleep(0.25)
                self._write_to_device()
            else:
                while (bytes_waiting // 14) > 0:
                    r = self._read_from_device()
                    bytes_waiting = self._ser.in_waiting
                    if len(r) < 14:
                        logging.warn('short packet length')
                    else:
                        existing_recipe.append(r)
                        if r[4:5] == b'\xAF' or r[4:5] == b'\x00':
                            end_of_recipe = True
                        continue
        return existing_recipe

    def auto_connect(self):
        """Starts a thread that will automatically connect to the roaster when
        it is plugged in."""
        self.connected = False
        self.auto_connect_thread = threading.Thread(target=self._auto_connect)
        self.auto_connect_thread.start()

    def _auto_connect(self):
        """Attempts to connect to the roaster every quarter of a second."""
        while(self._cont.value):
            try:
                self.connect()
                self.connected = True
                break
            except exceptions.RoasterLookupError:
                time.sleep(.25)

    def disconnect(self):
        """Stops the communication loop to the roaster. Note that this will not
        actually stop the roaster itself, but will allow the program to exit
        cleanly."""
        self._cont.value = 0

    def _now(self):
        return int(time.time() * 1000)

    def comm(self):
        """Main communications loop to the roaster. If the packet is not 14
        bytes exactly, the packet will not be opened. If an update data
        function is available, it will be called when the packet is opened."""
        while(self._cont.value):
            start = self._now()
            if self._write_to_device() is False:
                continue

            bytes_waiting = self._ser.in_waiting
            if bytes_waiting >= 14:
                loops = bytes_waiting // 14
                for n in range(0, loops):
                    r = self._read_from_device()
                    if len(r) != 14:
                        logging.warn(
                                'unexpected length [{}] of data: {}'
                                .format(len(r), r))
                    else:
                        if(r[-2:] == self._footer):
                            self._process_response(r)
                        else:
                            logging.warn('expected footer not present')

            total_ms = self._now() - start
            sleep_duration = 0.25 - (total_ms / 1000)
            if sleep_duration > 0:
                time.sleep(sleep_duration)

        self._ser.close()

    def _process_response(self, r):
        temp = struct.unpack(">H", r[10:-2])[0]
        if(temp == 65280):
            self.current_temp = 150
        elif(temp > 550 or temp < 150):
            logging.warn('temperature out of range: reinitializing...')
            self._initialize()
            return
        else:
            self.current_temp = temp

        if(self.update_data_func is not None):
            self.update_data_func()

    def timer(self):
        """Timer loop used to keep track of the time while roasting or
        cooling. If the time remaining reaches zero, the roaster will call the
        supplied state transistion function or the roaster will be set to
        the idle state."""
        while(self._cont.value):
            state = self.get_roaster_state()
            if(state == 'roasting' or state == 'cooling'):
                time.sleep(1)
                self.total_time += 1
                if(self.time_remaining > 0):
                    self.time_remaining -= 1
                else:
                    if(self.state_transition_func is not None):
                        self.state_transition_func()
                    else:
                        self.idle()
            else:
                time.sleep(0.01)

    def get_roaster_state(self):
        """Returns a string based upon the current state of the roaster. Will
        raise an exception if the state is unknown."""
        value = self._current_state.value
        if(value == b'\x02\x01'):
            return 'idle'
        elif(value == b'\x04\x04'):
            return 'cooling'
        elif(value == b'\x08\x01'):
            return 'sleeping'
        # handle null bytes as empty strings
        elif(value == b'\x00\x00' or value == b''):
            return 'connecting'
        elif(value == b'\x04\x02'):
            return 'roasting'
        else:
            return 'unknown'

    def generate_packet(self):
        """Generates a packet based upon the current class variables. Note that
        current temperature is not sent, as the original application sent zeros
        to the roaster for the current temperature."""
        roaster_time = utils.seconds_to_float(self._time_remaining.value)
        packet = (
            self._header.value +
            self._temp_unit.value +
            self._flags.value +
            self._current_state.value +
            struct.pack(">B", self._fan_speed.value) +
            struct.pack(">B", int(round(roaster_time * 10.0))) +
            struct.pack(">B", self._heat_setting.value) +
            b'\x00\x00' +
            self._footer)

        return packet

    def idle(self):
        """Sets the current state of the roaster to idle."""
        self._current_state.value = b'\x02\x01'

    def roast(self):
        """Sets the current state of the roaster to roast and begins
        roasting."""
        self._current_state.value = b'\x04\x02'

    def cool(self):
        """Sets the current state of the roaster to cool. The roaster expects
        that cool will be run after roast, and will not work as expected if ran
        before."""
        self._current_state.value = b'\x04\x04'

    def sleep(self):
        """Sets the current state of the roaster to sleep. Different than idle
        in that this will set double dashes on the roaster display rather than
        digits."""
        self._current_state.value = b'\x08\x01'

    def thermostat(self):
        """Utilizes a software PID controller to set the heat setting on the
        roaster given the current temperature and a target temperture."""
        p = 4.000
        i = 0.045
        d = 2.200
        controller = pid.PID(p, i, d)

        while(self._cont.value):
            output = controller.update(self.current_temp, self.target_temp)

            if(self.target_temp >= 460):
                if(output >= 30):
                    self.heat_setting = 3
                else:
                    if(self.heat_setting == 2):
                        self.heat_setting = 3
                    else:
                        self.heat_setting = 2
            elif(self.target_temp >= 430):
                if(output >= 30):
                    self.heat_setting = 3
                elif(output >= 20):
                    self.heat_setting = 2
                else:
                    if(self.heat_setting == 1):
                        self.heat_setting = 2
                    else:
                        self.heat_setting = 1
            elif(self.target_temp >= 350):
                if(output >= 30):
                    self.heat_setting = 3
                elif(output >= 20):
                    self.heat_setting = 2
                elif(output >= 10):
                    self.heat_setting = 1
                else:
                    if(self.heat_setting == 0):
                        self.heat_setting = 1
                    else:
                        self.heat_setting = 0
            else:
                if(output >= 30):
                    self.heat_setting = 3
                elif(output >= 20):
                    self.heat_setting = 2
                elif(output >= 10):
                    self.heat_setting = 1
                else:
                    self.heat_setting = 0
