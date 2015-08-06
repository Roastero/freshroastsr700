# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import unittest
import freshroastsr700


class TestFreshroastsr700(unittest.TestCase):
    """A test class for the freshroastsr700 module."""
    def setUp(self):
        """Sets up the freshroastsr700 object for testing."""
        self.roaster = freshroastsr700.freshroastsr700()

    def test_init_var_header(self):
        """Verifies _header is created on initialization properly."""
        self.assertEqual(self.roaster._header, b'\xAA\xAA')

    def test_init_var_temp_unit(self):
        """Verifies _temp_unit is created on initialization properly."""
        self.assertEqual(self.roaster._temp_unit, b'\x61\x74')

    def test_init_var_flags(self):
        """Verifies _flags is created on initialization properly."""
        self.assertEqual(self.roaster._flags, b'\x63')

    def test_init_var_control(self):
        """Verifies _control is created on initialization properly."""
        self.assertEqual(self.roaster._control, b'\x02\x01')

    def test_init_var_footer(self):
        """Verifies _footer is created on initialization properly."""
        self.assertEqual(self.roaster._footer, b'\xAA\xFA')

    def test_init_var_fan_speed(self):
        """Verifies fan_speed is created on initialization properly."""
        self.assertEqual(self.roaster.fan_speed, 0)

    def test_init_var_heat_setting(self):
        """Verifies heat_setting is created on initialization properly."""
        self.assertEqual(self.roaster.heat_setting, 0)

    def test_init_var_time_remaining(self):
        """Verifies time_remaining is created on initialization properly."""
        self.assertEqual(self.roaster.time_remaining, 0.0)

    def test_init_var_current_temp(self):
        """Verifies current_temp is created on initialization properly."""
        self.assertEqual(self.roaster.current_temp, 150)
