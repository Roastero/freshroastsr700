# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import unittest
import freshroastsr700

from freshroastsr700 import exceptions


class TestFreshroastsr700(unittest.TestCase):
    def setUp(self):
        self.roaster = freshroastsr700.freshroastsr700()

    def test_init_var_header(self):
        self.assertEqual(self.roaster._header, b'\xAA\xAA')

    def test_init_var_temp_unit(self):
        self.assertEqual(self.roaster._temp_unit, b'\x61\x74')

    def test_init_var_flags(self):
        self.assertEqual(self.roaster._flags, b'\x63')

    def test_init_var_current_state(self):
        self.assertEqual(self.roaster._current_state, b'\x02\x01')

    def test_init_var_footer(self):
        self.assertEqual(self.roaster._footer, b'\xAA\xFA')

    def test_init_var_fan_speed(self):
        self.assertEqual(self.roaster._fan_speed, 1)

    def test_init_var_heat_setting(self):
        self.assertEqual(self.roaster._heat_setting, 0)

    def test_init_var_time_remaining(self):
        self.assertEqual(self.roaster._time_remaining, 0.0)

    def test_init_var_current_temp(self):
        self.assertEqual(self.roaster._current_temp, 150)

    def test_generate_packet(self):
        packet = self.roaster.generate_packet()
        self.assertEqual(
            packet, b'\xaa\xaaatc\x02\x01\x01\x00\x00\x00\x00\xaa\xfa')

    def test_open_packet_not_150(self):
        self.roaster.open_packet(
            b'\xaa\xaaatc\x02\x01\x01\x00\x00\x01\x60\xaa\xfa')
        self.assertEqual(self.roaster.current_temp, 352)

    def test_open_packet_before_over_150(self):
        self.roaster.open_packet(
            b'\xaa\xaaatc\x02\x01\x01\x00\x00\xff\x00\xaa\xfa')
        self.assertEqual(self.roaster._current_temp, 150)

    def test_idle(self):
        self.roaster.idle()
        self.assertEqual(self.roaster._current_state, b'\x02\x01')

    def test_roast(self):
        self.roaster.roast()
        self.assertEqual(self.roaster._current_state, b'\x04\x02')

    def test_cool(self):
        self.roaster.cool()
        self.assertEqual(self.roaster._current_state, b'\x04\x04')

    def test_sleep(self):
        self.roaster.sleep()
        self.assertEqual(self.roaster._current_state, b'\x08\x01')

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
        self.assertEqual(self.roaster.time_remaining, 0.0)

    def test_setting_var_time_remaining_high(self):
        with self.assertRaises(exceptions.RoasterValueError):
            self.roaster.time_remaining = 10.0

    def test_setting_var_time_remaining_low(self):
        with self.assertRaises(exceptions.RoasterValueError):
            self.roaster.time_remaining = -1.0

    def test_setting_var_time_remaining_incorrect(self):
        with self.assertRaises(exceptions.RoasterValueError):
            self.roaster.time_remaining = 'w'

    def test_setting_var_time_remaining_correct(self):
        self.roaster.time_remaining = 5.6
        self.assertEqual(self.roaster.time_remaining, 5.6)

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
        self.assertFalse(self.roaster._cont)
