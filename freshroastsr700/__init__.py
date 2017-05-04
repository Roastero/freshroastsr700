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
    """A class to interface with a freshroastsr700 coffee roaster.

    Args:
        update_data_func (func): A function to call when this object
        receives new data from the hardware. Defaults to None.

        state_transition_func (func): A function to call when time_remaining
        counts down to 0 and the device is either in roasting or cooling
        state. Defaults to None.

        thermostat (bool): thermostat mode.
        if set to True, turns on thermostat mode.  In thermostat
        mode, freshroastsr700 takes control of heat_setting and does
        software PID control to hit the demanded target_temp. Defaults to
        False.

        kp (float): Kp value to use for PID control. Defaults to 0.06.

        ki (float): Ki value to use for PID control. Defaults to 0.0075.

        kd (float): Kd value to use for PID control. Defaults to 0.01.

        heater_segments (int): the pseudo-control range for the internal
        heat_controller object.  Defaults to 8.
    """
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
        # constants for protocol decoding
        self.LOOKING_FOR_HEADER_1 = 0
        self.LOOKING_FOR_HEADER_2 = 1
        self.PACKET_DATA = 2
        self.LOOKING_FOR_FOOTER_2 = 3
        # constants for connection state monitoring
        self.CS_NOT_CONNECTED = -2
        self.CS_ATTEMPTING_CONNECT = -1
        self.CS_CONNECTING = 0
        self.CS_CONNECTED = 1
        # constants for connection attempt type
        self.CA_NONE = 0
        self.CA_AUTO = 1
        self.CA_SINGLE_SHOT = 2

        self._create_update_data_system(update_data_func)
        self._create_state_transition_system(state_transition_func)

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

        self._disconnect = sharedctypes.Value('i', 0)
        self._teardown = sharedctypes.Value('i', 0)

        # for SW PWM heater setting
        self._heater_level = sharedctypes.Value('i', 0)
        # the following vars are not process-safe, do not access them
        # from the comm or timer threads, nor from the callbacks.
        self._thermostat = thermostat
        self._pid_kp = kp
        self._pid_ki = ki
        self._pid_kd = kd
        self._heater_bangbang_segments = heater_segments

        # initialize to 'not connected'
        self._connected = sharedctypes.Value('i', 0)
        self._connect_state = sharedctypes.Value('i', self.CS_NOT_CONNECTED)
        # initialize to 'not trying to connect'
        self._attempting_connect = sharedctypes.Value('i', self.CA_NONE)

        # create comm process
        self.comm_process = mp.Process(
            target=self._comm,
            args=(
                self._thermostat,
                self._pid_kp,
                self._pid_ki,
                self._pid_kd,
                self._heater_bangbang_segments,
                self.update_data_event,))
        self.comm_process.daemon = True
        self.comm_process.start()
        # create timer process that counts down time_remaining
        self.time_process = mp.Process(
            target=self._timer,
            args=(
                self.state_transition_event,))
        self.time_process.daemon = True
        self.time_process.start()

    def _create_update_data_system(
            self, update_data_func, setFunc=True, createThread=False):
        # these callbacks cannot be called from another process in Windows.
        # Therefore, spawn a thread belonging to the calling process
        # instead.
        # the comm and timer processes will set events that the threads
        # will listen for to initiate the callbacks

        # only create the mp.Event once -
        # to mimic create_state_transition_system, for future-proofing
        # (in this case, currently, this is only called at __init__() time)
        if not hasattr(self, 'update_data_event'):
            self.update_data_event = mp.Event()
        # only create the thread.Event once - this is used to exit
        # the callback thread
        if not hasattr(self, 'update_data_callback_kill_event'):
            self.update_data_callback_kill_event = threading.Event()
        # destroy an existing thread if we had created one previously
        if(hasattr(self, 'update_data_thread') and
           self.update_data_thread is not None):
            # let's tear this down. To kill it, two events must be set...
            # in the right sequence!
            self.update_data_callback_kill_event.set()
            self.update_data_event.set()
            self.update_data_thread.join()
        if setFunc:
            self.update_data_func = update_data_func
        if self.update_data_func is not None:
            if createThread:
                self.update_data_callback_kill_event.clear()
                self.update_data_thread = threading.Thread(
                    name='sr700_update_data',
                    target=self.update_data_run,
                    args=(self.update_data_event,),
                    daemon=True
                    )
        else:
            self.update_data_thread = None

    def _create_state_transition_system(
            self, state_transition_func, setFunc=True, createThread=False):
        # these callbacks cannot be called from another process in Windows.
        # Therefore, spawn a thread belonging to the calling process
        # instead.
        # the comm and timer processes will set events that the threads
        # will listen for to initiate the callbacks

        # only create the mp.Event once - this fn can get called more
        # than once, by __init__() and by set_state_transition_func()
        if not hasattr(self, 'state_transition_event'):
            self.state_transition_event = mp.Event()
        # only create the thread.Event once - this is used to exit
        # the callback thread
        if not hasattr(self, 'state_transition_callback_kill_event'):
            self.state_transition_callback_kill_event = threading.Event()
        # destroy an existing thread if we had created one previously
        if(hasattr(self, 'state_transition_thread') and
           self.state_transition_thread is not None):
            # let's tear this down. To kill it, two events must be set...
            # in the right sequence!
            self.state_transition_callback_kill_event.set()
            self.state_transition_event.set()
            self.state_transition_thread.join()
        if setFunc:
            self.state_transition_func = state_transition_func
        if self.state_transition_func is not None:
            if createThread:
                self.state_transition_callback_kill_event.clear()
                self.state_transition_thread = threading.Thread(
                    name='sr700_state_transition',
                    target=self.state_transition_run,
                    args=(self.state_transition_event,),
                    daemon=True
                    )
        else:
            self.state_transition_thread = None

    @property
    def fan_speed(self):
        """Get/Set fan speed. Can be 1 to 9 inclusive.

        Args:
            Setter: fan_speed (int): fan speed

        Returns:
            Getter: (int): fan speed
        """
        return self._fan_speed.value

    @fan_speed.setter
    def fan_speed(self, value):
        """Verifies the value is between 1 and 9 inclusively."""
        if value not in range(1, 10):
            raise exceptions.RoasterValueError

        self._fan_speed.value = value

    @property
    def heat_setting(self):
        """Get/Set heat setting, 0 to 3 inclusive. 0=off, 3=high.
        Do not set when running freshroastsr700 in thermostat mode.

        Args:
            Setter: heat_setting (int): heat setting

        Returns:
            Getter: (int): heat setting
        """
        return self._heat_setting.value

    @heat_setting.setter
    def heat_setting(self, value):
        """Verifies that the heat setting is between 0 and 3."""
        if value not in range(0, 4):
            raise exceptions.RoasterValueError

        self._heat_setting.value = value

    @property
    def target_temp(self):
        """Get/Set the target temperature for this package's built-in software
        PID controler.  Only used when freshroastsr700 is instantiated with
        thermostat=True.

        Args:
            Setter: value (int): a target temperature in degF between 150
            and 551.

        Returns:
            Getter: (int) target temperature in degF between 150
            and 551
        """
        return self._target_temp.value

    @target_temp.setter
    def target_temp(self, value):
        if value not in range(150, 551):
            raise exceptions.RoasterValueError

        self._target_temp.value = value

    @property
    def current_temp(self):
        """Current temperature of the roast chamber as reported by hardware.

        Returns:
            (int) current temperature, in degrees Fahrenheit
        """
        return self._current_temp.value

    @current_temp.setter
    def current_temp(self, value):
        if value not in range(150, 551):
            raise exceptions.RoasterValueError

        self._current_temp.value = value

    @property
    def time_remaining(self):
        """The amount of time, in seconds, remaining until a call to
        the state_transition_func is made. can be set to an arbitrary value
        up to 600 seconds at any time.  When a new value is set,
        freshroastsr700 will count down from this new value down to 0.

        time_remaining is decremented to 0 only when in a roasting or
        cooling state.  In other states, the value is not touched.

        Args:
            Setter: time_remaining (int): tiem remaining in seconds

        Returns:
            Getter: time_remaining(int): time remaining, in seconds
        """
        return self._time_remaining.value

    @time_remaining.setter
    def time_remaining(self, value):
        self._time_remaining.value = value

    @property
    def total_time(self):
        """The total time this instance has been in roasting or cooling
        state sicne the latest roast began.

        Returns:
            total_time (int): time, in seconds
        """
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

    @property
    def connected(self):
        """A getter method for _connected. Indicates that the
        this software is currently communicating with FreshRoast SR700
        hardware."""
        return self._connected.value

    @property
    def connect_state(self):
        """A getter method for _connect_state. Indicates the current
        connection state this software is in for FreshRoast SR700
        hardware.
        Returns:
            freshroastsr700.CS_NOT_CONNECTED
                the software is not currenting communicating with hardware,
                neither was it instructed to do so.
                A previously failed connection attempt will also result
                in this state.
            freshroastsr700.CS_ATTEMPTING_CONNECT
                A call to auto_connect() or connect() was made, and the
                software is currently attempting to connect to hardware.
            freshroastsr700.CS_CONNECTED
                The hardware was found, and the software is communicating
                with the hardware.
        """
        return self._connect_state.value

    def set_state_transition_func(self, func):
        """THIS FUNCTION MUST BE CALLED BEFORE CALLING
        freshroastsr700.auto_connect().

        Set, or re-set, the state transition function callback.
        The supplied function will be called from a separate thread within
        freshroastsr700, triggered by a separate, internal child process.
        This function will fail if the freshroastsr700 device is already
        connected to hardware, because by that time, the timer process
        and thread have already been spawned.

        Args:
            state_transition_func (func): the function to call for every
            state transition.  A state transition occurs whenever the
            freshroastsr700's time_remaining value counts down to 0.

        Returns:
            nothing
       """
        if self._connected.value:
            logging.error("freshroastsr700.set_state_transition_func must be "
                          "called before freshroastsr700.auto_connect()."
                          " Not registering func.")
            return False
        # no connection yet. so OK to set func pointer
        self._create_state_transition_system(func)
        return True

    def update_data_run(self, event_to_wait_on):
        """This is the thread that listens to an event from
           the comm process to execute the update_data_func callback
           in the context of the main process.
           """
        # with the daemon=Turue setting, this thread should
        # quit 'automatically'
        while event_to_wait_on.wait():
            event_to_wait_on.clear()
            if self.update_data_callback_kill_event.is_set():
                return
            self.update_data_func()

    def state_transition_run(self, event_to_wait_on):
        """This is the thread that listens to an event from
           the timer process to execute the state_transition_func callback
           in the context of the main process.
           """
        # with the daemon=Turue setting, this thread should
        # quit 'automatically'
        while event_to_wait_on.wait():
            event_to_wait_on.clear()
            if self.state_transition_callback_kill_event.is_set():
                return
            self.state_transition_func()

    def _connect(self):
        """Do not call this directly - call auto_connect() or connect(),
        which will call _connect() for you.

        Connects to the roaster and creates communication thread.
        Raises a RoasterLokkupError exception if the hardware is not found.
        """
        # the following call raises a RoasterLookupException when the device
        # is not found. It is
        port = utils.find_device('1A86:5523')
        # on some systems, after the device port is added to the device list,
        # it can take up to 20 seconds after USB insertion for
        # the port to become available... (!)
        # let's put a safety timeout in here as a precaution
        wait_timeout = time.time() + 40.0  # should be PLENTY of time!
        # let's update the _connect_state while we're at it...
        self._connect_state.value = self.CS_CONNECTING
        connect_success = False
        while time.time() < wait_timeout:
            try:
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
                connect_success = True
                break
            except serial.SerialException:
                time.sleep(0.5)
        if not connect_success:
            # timeout on attempts
            raise exceptions.RoasterLookupError

        self._initialize()

    def _initialize(self):
        """Sends the initialization packet to the roaster."""
        self._header.value = b'\xAA\x55'
        self._current_state.value = b'\x00\x00'
        s = self._generate_packet()
        self._ser.write(s)
        self._header.value = b'\xAA\xAA'
        self._current_state.value = b'\x02\x01'

        return self._read_existing_recipe()

    def _write_to_device(self):
        success = False
        try:
            packet = self._generate_packet()
            logging.debug('WR: ' + str(binascii.hexlify(packet)))
            self._ser.write(packet)
            success = True
        except serial.serialutil.SerialException:
            logging.error('caught serial exception writing')
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

    def connect(self):
        """Attempt to connect to hardware immediately.  Will not retry.
        Check freshroastsr700.connected or freshroastsr700.connect_state
        to verify result.
        Raises:
            freshroastsr700.exeptions.RoasterLookupError
                No hardware connected to the computer.
        """
        self._start_connect(self.CA_SINGLE_SHOT)
        while(self._connect_state.value == self.CS_ATTEMPTING_CONNECT or
              self._connect_state.value == self.CS_CONNECTING):
            time.sleep(0.1)
        if self.CS_CONNECTED != self._connect_state.value:
            raise exceptions.RoasterLookupError

    def auto_connect(self):
        """Starts a thread that will automatically connect to the roaster when
        it is plugged in."""
        self._start_connect(self.CA_AUTO)

    def _start_connect(self, connect_type):
        """Starts the connection process, as called (internally)
        from the user context, either from auto_connect() or connect().
        Never call this from the _comm() process context.
        """
        if self._connect_state.value != self.CS_NOT_CONNECTED:
            # already done or in process, assume success
            return

        self._connected.value = 0
        self._connect_state.value = self.CS_ATTEMPTING_CONNECT
        # tell comm process to attempt connection
        self._attempting_connect.value = connect_type

        # EXTREMELY IMPORTANT - for this to work at all in Windows,
        # where the above processes are spawned (vs forked in Unix),
        # the thread objects (as sattributes of this object) must be
        # assigned to this object AFTER we have spawned the processes.
        # That way, multiprocessing can pickle the freshroastsr700
        # successfully. (It can't pickle thread-related stuff.)
        if self.update_data_func is not None:
            # Need to launch the thread that will listen to the event
            self._create_update_data_system(
                None, setFunc=False, createThread=True)
            self.update_data_thread.start()
        if self.state_transition_func is not None:
            # Need to launch the thread that will listen to the event
            self._create_state_transition_system(
                None, setFunc=False, createThread=True)
            self.state_transition_thread.start()

    def _auto_connect(self):
        """Attempts to connect to the roaster every quarter of a second."""
        while not self._teardown.value:
            try:
                self._connect()
                return True
            except exceptions.RoasterLookupError:
                time.sleep(.25)
        return False

    def disconnect(self):
        """Stops the communication loop to the roaster. Note that this will not
        actually stop the roaster itself."""
        self._disconnect.value = 1

    def terminate(self):
        """Stops the communication loop to the roaster and closes down all
        communication processes. Note that this will not
        actually stop the roaster itself.
        You will need to instantiate a new freshroastsr700 object after
        calling this function, in order to re-start communications with
        the hardware.
        """
        self.disconnect()
        self._teardown.value = 1

    def _comm(self, thermostat=False,
              kp=0.06, ki=0.0075, kd=0.01,
              heater_segments=8, update_data_event=None):
        """Do not call this directly - call auto_connect(), which will spawn
        comm() for you.

        This is the main communications loop to the roaster.
        whenever a valid packet is received from the device, if an
        update_data_event is available, it will be signalled.

        Args:
            thermostat (bool): thermostat mode.
            if set to True, turns on thermostat mode.  In thermostat
            mode, freshroastsr700 takes control of heat_setting and does
            software PID control to hit the demanded target_temp.

            kp (float): Kp value to use for PID control. Defaults to 0.06.

            ki (float): Ki value to use for PID control. Defaults to 0.0075.

            kd (float): Kd value to use for PID control. Defaults to 0.01.

            heater_segments (int): the pseudo-control range for the internal
            heat_controller object.  Defaults to 8.

            update_data_event (multiprocessing.Event): If set, allows the
            comm_process to signal to the parent process that new device data
            is available.

        Returns:
            nothing
        """
        # since this process is started with daemon=True, it should exit
        # when the owning process terminates. Therefore, safe to loop forever.
        while not self._teardown.value:

            # waiting for command to attempt connect
            # print( "waiting for command to attempt connect")
            while self._attempting_connect.value == self.CA_NONE:
                time.sleep(0.25)
                if self._teardown.value:
                    break
            # if we're tearing down, bail now.
            if self._teardown.value:
                break

            # we got the command to attempt to connect
            # change state to 'attempting_connect'
            self._connect_state.value = self.CS_ATTEMPTING_CONNECT
            # attempt connection
            if self.CA_AUTO == self._attempting_connect.value:
                # this call will block until a connection is achieved
                # it will also set _connect_state to CS_CONNECTING
                # if appropriate
                if self._auto_connect():
                    # when we unblock, it is an indication of a successful
                    # connection
                    self._connected.value = 1
                    self._connect_state.value = self.CS_CONNECTED
                else:
                    # failure, normally due to a timeout
                    self._connected.value = 0
                    self._connect_state.value = self.CS_NOT_CONNECTED
                    # we failed to connect - start over from the top
                    # reset flag
                    self._attempting_connect.value = self.CA_NONE
                    continue

            elif self.CA_SINGLE_SHOT == self._attempting_connect.value:
                # try once, now, if failure, start teh big loop over
                try:
                    self._connect()
                    self._connected.value = 1
                    self._connect_state.value = self.CS_CONNECTED
                except exceptions.RoasterLookupError:
                    self._connected.value = 0
                    self._connect_state.value = self.CS_NOT_CONNECTED
                if self._connect_state.value != self.CS_CONNECTED:
                    # we failed to connect - start over from the top
                    # reset flag
                    self._attempting_connect.value = self.CA_NONE
                    continue
            else:
                # shouldn't be here
                # reset flag
                self._attempting_connect.value = self.CA_NONE
                continue

            # We are connected!
            # print( "We are connected!")
            # reset flag right away
            self._attempting_connect.value = self.CA_NONE

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
            write_errors = 0
            read_errors = 0
            while not self._disconnect.value:
                start = datetime.datetime.now()
                # write to device
                if not self._write_to_device():
                    logging.error('comm - _write_to_device() failed!')
                    write_errors += 1
                    if write_errors > 3:
                        # it's time to consider the device as being "gone"
                        logging.error('comm - 3 successive write '
                                      'failures, disconnecting.')
                        self._disconnect.value = 1
                        continue
                else:
                    # reset write_errors
                    write_errors = 0

                # read from device
                try:
                    while self._ser.in_waiting:
                        _byte = self._ser.read(1)
                        read_state, r, err = (
                            self._process_reponse_byte(
                                read_state, _byte, r, update_data_event))
                except IOError:
                    # typically happens when device is suddenly unplugged
                    logging.error('comm - read from device failed!')
                    read_errors += 1
                    if write_errors > 3:
                        # it's time to consider the device as being "gone"
                        logging.error('comm - 3 successive read '
                                      'failures, disconnecting.')
                        self._disconnect.value = 1
                        continue
                else:
                    read_errors = 0

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
                        # read bang-bang heater output array element & apply it
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
            # reset disconnect flag
            self._disconnect.value = 0
            # reset connection values
            self._connected.value = 0
            self._connect_state.value = self.CS_NOT_CONNECTED
            # print("We are disconnected.")

    def _process_reponse_byte(self, read_state, _byte, r, update_data_event):
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
                        self._process_reponse_byte(
                            read_state, b'\xAA', r, update_data_event))
                    read_state, r, err = (
                        self._process_reponse_byte(
                            read_state, b'\xFA', r, update_data_event))

        elif self.LOOKING_FOR_FOOTER_2 == read_state:
            if b'\xFA' == _byte:
                # OK we have a full packet - PROCESS PACKET
                err = self._process_response_data(r, update_data_event)
                read_state = self.LOOKING_FOR_HEADER_1
            else:
                # the last byte was not the beginning of the footer
                r.append(b'\xAA')
                read_state = self.PACKET_DATA
                read_state, r, err = self._process_reponse_byte(
                    read_state, _byte, r, update_data_event)
        else:
            # error state, shouldn't happen...
            logging.error('_process_reponse_byte - invalid read_state %d' %
                          read_state)
            read_state = self.LOOKING_FOR_HEADER_1
            err = True
        return read_state, r, err

    def _process_response_data(self, r, update_data_event):
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

            if(update_data_event is not None):
                update_data_event.set()
        return err

    def _timer(self, state_transition_event=None):
        """Timer loop used to keep track of the time while roasting or
        cooling. If the time remaining reaches zero, the roaster will call the
        supplied state transistion function or the roaster will be set to
        the idle state."""
        while not self._teardown.value:
            state = self.get_roaster_state()
            if(state == 'roasting' or state == 'cooling'):
                time.sleep(1)
                self.total_time += 1
                if(self.time_remaining > 0):
                    self.time_remaining -= 1
                else:
                    if(state_transition_event is not None):
                        state_transition_event.set()
                    else:
                        self.idle()
            else:
                time.sleep(0.01)

    def get_roaster_state(self):
        """Returns a string based upon the current state of the roaster. Will
        raise an exception if the state is unknown.

        Returns:
            'idle' if idle,
            'sleeping' if sleeping,
            'cooling' if cooling,
            'roasting' if roasting,
            'connecting' if in hardware connection phase,
            'unknown' otherwise
        """
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

    def _generate_packet(self):
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
    """A class to do gross-level pulse modulation on a bang-bang interface.

    Args:
        number_of_segments (int): the resolution of the heat_controller.
        Defaults to 8.  for number_of_segments=N, creates a heat_controller
        that varies the heat between 0..N inclusive, in integer increments,
        where 0 is no heat, and N is full heat.  The bigger the number, the
        less often the heat value can be changed, because this object is
        designed to be called at a regular time interval to output N binary
        values before rolling over or picking up the latest commanded heat
        value.
    """
    def __init__(self, number_of_segments=8):
        # num_segments determines how many time samples are used to produce
        # the output.  This effectively translates to a number of output
        # levels on the bang-bang controller.  If number_of_segments == 8,
        # for example, then, possible output 'levels' are 0,1,2,...8.
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
        """Set/Get the current desired output level. Must be between 0 and
        number_of_segments inclusive.

        Args:
            Setter: value (int): heat_level value,
            between 0 and number_of_segments inclusive.

        Returns:
            Getter (int): heat level"""
        return self._heat_level

    @heat_level.setter
    def heat_level(self, value):
        """Set the desired output level. Must be between 0 and
        number_of_segments inclusive."""
        if value < 0:
            self._heat_level = 0
        elif round(value) > self._num_segments:
            self._heat_level = self._num_segments
        else:
            self._heat_level = int(round(value))

    def generate_bangbang_output(self):
        """Generates the latest on or off pulse in
           the string of on (True) or off (False) pulses
           according to the desired heat_level setting.  Successive calls
           to this function will return the next value in the
           on/off array series.  Call this at control loop rate to
           obtain the necessary on/off pulse train.
           This system will not work if the caller expects to be able
           to specify a new heat_level at every control loop iteration.
           Only the value set at every number_of_segments iterations
           will be picked up for output! Call about_to_rollover to determine
           if it's time to set a new heat_level, if a new level is desired."""
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
           pick up the latest commanded heat_level value and run a PID
           controller iteration."""
        return self._current_index >= self._num_segments
