# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Mark Spicer
# Made available under the MIT license.

import time
import datetime
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
    def __init__(self,
                 update_data_func=None,
                 state_transition_func=None,
                 thermostat=False,
                 kp=0.06, ki=0.0075, kd=0.01,
                 heater_segments=8):
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

        # for SW PWM heater setting
        self._heater_level = sharedctypes.Value('i', 0)
        # the following vars are not process-safe, do not access them
        # from the comm or timer threads, nor from the callbacks.
        self._thermostat = thermostat
        self._pid_kp = kp
        self._pid_ki = ki
        self._pid_kd = kd
        self._heater_bangbang_segments = heater_segments

        # constants for protocol decoding
        self.LOOKING_FOR_HEADER_1 = 0
        self.LOOKING_FOR_HEADER_2 = 1
        self.PACKET_DATA = 2
        self.LOOKING_FOR_FOOTER_2 = 3

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

    @property
    def heater_level(self):
        """A getter method for _heater_level. Only used when
           thermostat=True.  Driven by built-in PID controller.
           Min will always be zero, max will be heater_segments
           (optional instantiation parameter, defaults to 8)."""
        return self._heater_level.value

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

        self.comm_process = mp.Process(
            target=self.comm,
            args=(
                self._thermostat,
                self._pid_kp,
                self._pid_ki,
                self._pid_kd,
                self._heater_bangbang_segments,))
        self.comm_process.daemon = True
        self.comm_process.start()
        self.time_process = mp.Process(target=self.timer)
        self.time_process.daemon = True
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

    def comm(self, thermostat=False,
             kp=0.06, ki=0.0075, kd=0.01,
             heater_segments=8):
        """Main communications loop to the roaster. If the packet is not 14
        bytes exactly, the packet will not be opened. If an update data
        function is available, it will be called when the packet is opened."""
        # Initialize PID controller if thermostat function was specified at
        # init time
        pidc = None
        heater = None
        if(thermostat):
            pidc = pid.PID(kp, ki, kd,
                           Output_max=heater_segments,
                           Output_min=0
                           )
            heater = heat_controller(number_of_segments=heater_segments)

        read_state = self.LOOKING_FOR_HEADER_1
        r = []
        while(self._cont.value):
            start = datetime.datetime.now()
            # write to device
            if self._write_to_device() is False:
                # TODO - if _write_to_device() really returns false,
                # this codebase will spiral out of control.
                # _write_to_device() being false means a write exception
                # has occurred, and this code is now
                # attempting to spawn a thread using _auto_connect()
                # from here (we're in a child process...),
                # which attempts to spawn another copy of
                # this process.  Needs review.
                logging.error('comm - _write_to_device() failed, expect chaos')
                continue

            # read from device
            while self._ser.in_waiting:
                _byte = self._ser.read(1)
                read_state, r, err = (
                    self._process_reponse_byte(read_state, _byte, r))

            # next, PID controller calcs when roasting.
            if thermostat:
                if 'roasting' == self.get_roaster_state():
                    if heater.about_to_rollover():
                        # it's time to use the PID controller value
                        # and set new output level on heater!
                        output = pidc.update(
                            self.current_temp, self.target_temp)
                        heater.heat_level = output
                        # make this number visible to other processes...
                        self._heater_level.value = heater.heat_level
                    # read bang-bang heater output array element and apply it
                    if heater.generate_bangbang_output():
                        # ON
                        self.heat_setting = 3
                    else:
                        # OFF
                        self.heat_setting = 0
                else:
                    # for all other states, heat_level = OFF
                    heater.heat_level = 0
                    # make this number visible to other processes...
                    self._heater_level.value = heater.heat_level
                    self.heat_setting = 0

            # calculate sleep time to stick to 0.25sec period
            comp_time = datetime.datetime.now() - start
            sleep_duration = 0.25 - comp_time.total_seconds()
            if sleep_duration > 0:
                time.sleep(sleep_duration)

        self._ser.close()

    def _process_reponse_byte(self, read_state, _byte, r):
        err = False
        if self.LOOKING_FOR_HEADER_1 == read_state:
            if b'\xAA' == _byte:
                read_state = self.LOOKING_FOR_HEADER_2
        elif self.LOOKING_FOR_HEADER_2 == read_state:
            if b'\xAA' == _byte:
                read_state = self.PACKET_DATA
                # reset packet array now...
                r = []
            else:
                read_state = self.LOOKING_FOR_HEADER_1
        elif self.PACKET_DATA == read_state:
            if b'\xAA' == _byte:
                # this could be the start of an end of packet marker
                read_state = self.LOOKING_FOR_FOOTER_2
            else:
                r.append(_byte)
                # SR700 FW bug - if current temp is 250 degF (0xFA),
                # the FW does not transmit the footer at all.
                # fake the footer here.
                if(len(r) == 10 and b'\xFA' == _byte):
                    # we will 'fake' a footer to make this decoder work
                    # as intended
                    read_state, r, _ = (
                        self._process_reponse_byte(read_state, b'\xAA', r))
                    read_state, r, err = (
                        self._process_reponse_byte(read_state, b'\xFA', r))

        elif self.LOOKING_FOR_FOOTER_2 == read_state:
            if b'\xFA' == _byte:
                # OK we have a full packet - PROCESS PACKET
                err = self._process_response_data(r)
                read_state = self.LOOKING_FOR_HEADER_1
            else:
                # the last byte was not the beginning of the footer
                r.append(b'\xAA')
                read_state = self.PACKET_DATA
                read_state, r, err = self._process_reponse_byte(
                    read_state, _byte, r)
        else:
            # error state, shouldn't happen...
            logging.error('_process_reponse_byte - invalid read_state %d' %
                          read_state)
            read_state = self.LOOKING_FOR_HEADER_1
            err = True
        return read_state, r, err

    def _process_response_data(self, r):
        err = False
        if len(r) != 10:
            logging.warn('read packet data len not 10, got: %d' % len(r))
            logging.warn('RD: ' + str(binascii.hexlify(b''.join(r))))
            err = True
        else:
            temp = struct.unpack(">H", b''.join(r[8:10]))[0]
            if(temp == 65280):
                self.current_temp = 150
            elif(temp > 550 or temp < 150):
                logging.warn('temperature out of range: reinitializing...')
                self._initialize()
                err = True
                return
            else:
                self.current_temp = temp

            if(self.update_data_func is not None):
                self.update_data_func()
        return err

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


class heat_controller(object):
    """A class to do gross-level pulse modulation on a bang-bang interface."""
    def __init__(self, number_of_segments=8):
        # num_segments determines how many time samples are used to produce
        # the output.  This effectively translates to a number of output
        # levels on the bang-bang controller.  If number_of_segments == 8,
        # for example, then, possible output 'levels' are 0,1,2,...7.
        # Depending on the output
        # rate and the load's time constant, the result could be perceived
        # as discrete lumps rather than an effective average output.
        # higer rate of output is better than slower.
        # This code does not attempt to control the rate of output,
        # that is left to the caller.
        self._num_segments = number_of_segments
        self._output_array = [[0 for x in range(self._num_segments)]
                              for x in range(1+self._num_segments)]
        # I'm sure there's a great way to do this algorithmically for
        # all possible num_segments...
        if 4 == self._num_segments:
            self._output_array[0] = [False, False, False, False]
            self._output_array[1] = [True, False, False, False]
            self._output_array[2] = [True, False, True, False]
            self._output_array[3] = [True, True, True, False]
            self._output_array[4] = [True, True, True, True]
        elif 8 == self._num_segments:
            self._output_array[0] = [False, False, False, False,
                                     False, False, False, False]
            self._output_array[1] = [True, False, False, False,
                                     False, False, False, False]
            self._output_array[2] = [True, False, False, False,
                                     True, False, False, False]
            self._output_array[3] = [True, False, False, True,
                                     False, False, True, False]
            self._output_array[4] = [True, False, True, False,
                                     True, False, True, False]
            self._output_array[5] = [True, True, False, True,
                                     True, False, True, False]
            self._output_array[6] = [True, True, True, False,
                                     True, True, True, False]
            self._output_array[7] = [True, True, True, True,
                                     True, True, True, False]
            self._output_array[8] = [True, True, True, True,
                                     True, True, True, True]
        else:
            # note that the most effective pulse modulation is one where
            # ones and zeroes are as temporarily spread as possible.
            # Example, for a 4-segment output,
            # [1,1,0,0] is not as effective as/lumpier than
            # [1,0,1,0], even though they supply the same energy.
            # If the output rate is much greater than the load's time constant,
            # this difference will not be percpetible.
            # Here, we're just stuffing early slots with ones... lumpier
            for i in range(1+self._num_segments):
                for j in range(self._num_segments):
                    self._output_array[i][j] = j < i
        # prepare for output
        self._heat_level = 0
        self._heat_level_now = 0
        self._current_index = 0

    @property
    def heat_level(self):
        """The desired output level."""
        return self._heat_level

    @heat_level.setter
    def heat_level(self, value):
        """Set the desired output level. """
        if value < 0:
            self._heat_level = 0
        elif round(value) > self._num_segments:
            self._heat_level = self._num_segments
        else:
            self._heat_level = int(round(value))

    def generate_bangbang_output(self):
        """Generates the latest on or off pulse in
           the string of on (True) or off (False) pulses
           according to the desired heat_level.  Successive calls
           to this function will return the next value in the
           on/off array series.  Call this at control loop rate to
           obtain the necessary on/off pulse train.
           This system will not work if the caller expects to be able
           to specify a new heat_level at every control loop iteration.
           Only the value set at every number_of_segments iterations
           will be picked up for output!"""
        if self._current_index >= self._num_segments:
            # we're due to switch over to the next
            # commanded heat_level
            self._heat_level_now = self._heat_level
            # reset array index
            self._current_index = 0
        # return output
        out = self._output_array[self._heat_level_now][self._current_index]
        self._current_index += 1
        return out

    def about_to_rollover(self):
        """This method indicates that the next call to generate_bangbang_output
           is a wraparound read.  Use this to determine if it's time to
           run the PID controller iteration again."""
        return self._current_index >= self._num_segments
