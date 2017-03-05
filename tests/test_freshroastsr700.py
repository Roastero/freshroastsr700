# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Mark Spicer
# Made available under the MIT license.

import unittest
import freshroastsr700

from freshroastsr700 import exceptions


class TestFreshroastsr700(unittest.TestCase):
    def setUp(self):
        self.roaster = freshroastsr700.freshroastsr700(thermostat=True)

    def test_init_var_header(self):
        self.assertEqual(self.roaster._header.value, b'\xAA\xAA')

    def test_init_var_temp_unit(self):
        self.assertEqual(self.roaster._temp_unit.value, b'\x61\x74')

    def test_init_var_flags(self):
        self.assertEqual(self.roaster._flags.value, b'\x63')

    def test_init_var_current_state(self):
        self.assertEqual(self.roaster._current_state.value, b'\x02\x01')

    def test_init_var_footer(self):
        self.assertEqual(self.roaster._footer, b'\xAA\xFA')

    def test_init_var_fan_speed(self):
        self.assertEqual(self.roaster._fan_speed.value, 1)

    def test_init_var_heat_setting(self):
        self.assertEqual(self.roaster._heat_setting.value, 0)

    def test_init_var_time_remaining(self):
        self.assertEqual(self.roaster.time_remaining, 0)

    def test_init_var_current_temp(self):
        self.assertEqual(self.roaster.current_temp, 150)

    def test_generate_packet(self):
        packet = self.roaster._generate_packet()
        self.assertEqual(
            packet, b'\xaa\xaaatc\x02\x01\x01\x00\x00\x00\x00\xaa\xfa')

    def test_idle(self):
        self.roaster.idle()
        self.assertEqual(self.roaster._current_state.value, b'\x02\x01')

    def test_roast(self):
        self.roaster.roast()
        self.assertEqual(self.roaster._current_state.value, b'\x04\x02')

    def test_cool(self):
        self.roaster.cool()
        self.assertEqual(self.roaster._current_state.value, b'\x04\x04')

    def test_sleep(self):
        self.roaster.sleep()
        self.assertEqual(self.roaster._current_state.value, b'\x08\x01')

    def test_getting_var_fan_speed(self):
        self.assertEqual(self.roaster.fan_speed, 1)

    def test_setting_var_fan_speed_high(self):
        with self.assertRaises(exceptions.RoasterValueError):
            self.roaster.fan_speed = 10

    def test_setting_var_fan_speed_low(self):
        with self.assertRaises(exceptions.RoasterValueError):
            self.roaster.fan_speed = 0

    def test_setting_var_fan_speed_incorrect(self):
        with self.assertRaises(exceptions.RoasterValueError):
            self.roaster.fan_speed = 'w'

    def test_seting_var_fan_speed_correct(self):
        self.roaster.fan_speed = 6
        self.assertEqual(self.roaster.fan_speed, 6)

    def test_getting_time_remaining(self):
        self.assertEqual(self.roaster.time_remaining, 0)

    def test_getting_heat_setting(self):
        self.assertEqual(self.roaster.heat_setting, 0)

    def test_setting_var_heat_setting_high(self):
        with self.assertRaises(exceptions.RoasterValueError):
            self.roaster.heat_setting = 4

    def test_setting_var_heat_setting_low(self):
        with self.assertRaises(exceptions.RoasterValueError):
            self.roaster.heat_setting = -1

    def test_setting_var_heat_setting_incorrect(self):
        with self.assertRaises(exceptions.RoasterValueError):
            self.roaster.heat_setting = 'w'

    def test_setting_var_heat_setting_correct(self):
        self.roaster.heat_setting = 3
        self.assertEqual(self.roaster.heat_setting, 3)

    def test_disconnect(self):
        self.roaster.disconnect()
        self.assertFalse(self.roaster._cont.value)

    def test_get_roaster_state_roasting(self):
        self.roaster._current_state.value = b'\x04\x02'
        self.assertEqual('roasting', self.roaster.get_roaster_state())

    def test_get_roaster_state_cooling(self):
        self.roaster._current_state.value = b'\x04\x04'
        self.assertEqual('cooling', self.roaster.get_roaster_state())

    def test_get_roaster_state_idle(self):
        self.roaster._current_state.value = b'\x02\x01'
        self.assertEqual('idle', self.roaster.get_roaster_state())

    def test_get_roaster_state_sleeping(self):
        self.roaster._current_state.value = b'\x08\x01'
        self.assertEqual('sleeping', self.roaster.get_roaster_state())

    def test_get_roaster_state_connecting(self):
        self.roaster._current_state.value = b'\x00\x00'
        self.assertEqual('connecting', self.roaster.get_roaster_state())

    def test_get_roaster_state_uknown(self):
        self.roaster._current_state.value = b'\x13\x41'
        self.assertEqual('unknown', self.roaster.get_roaster_state())

    def test_heat_controller_4_segment_output(self):
        heater = freshroastsr700.heat_controller(number_of_segments=4)
        heater.heat_level = 0
        self.assertFalse(heater.about_to_rollover())
        self.assertFalse(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertFalse(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertFalse(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertFalse(heater.generate_bangbang_output())
        self.assertTrue(heater.about_to_rollover())
        heater.heat_level = 1
        self.assertTrue(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertFalse(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertFalse(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertFalse(heater.generate_bangbang_output())
        self.assertTrue(heater.about_to_rollover())
        heater.heat_level = 2
        self.assertTrue(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertFalse(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertTrue(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertFalse(heater.generate_bangbang_output())
        self.assertTrue(heater.about_to_rollover())
        heater.heat_level = 3
        self.assertTrue(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertTrue(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertTrue(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertFalse(heater.generate_bangbang_output())
        self.assertTrue(heater.about_to_rollover())
        heater.heat_level = 4
        self.assertTrue(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertTrue(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertTrue(heater.generate_bangbang_output())
        self.assertFalse(heater.about_to_rollover())
        self.assertTrue(heater.generate_bangbang_output())
        self.assertTrue(heater.about_to_rollover())
