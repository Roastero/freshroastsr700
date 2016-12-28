# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Mark Spicer
# Made available under the MIT license.

import unittest
try:
    from unittest import mock
except ImportError:
    import mock
from freshroastsr700 import utils
from freshroastsr700 import exceptions


class TestUtils(unittest.TestCase):
    def test_frange_works(self):
        accepted_range = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        generated_range = [value for value in utils.frange(0.0, 0.9, 0.1, 1)]

        self.assertEqual(accepted_range, generated_range)

    @mock.patch(
        'freshroastsr700.utils.list_ports.comports',
        return_value=[
            ['/dev/tty1', 'test_element', '1AB5:5555'],
            ['/dev/tty2', 'test_element', '1A86:5523']])
    def test_find_device_with_device_available(self, mock_comports):
        device_path = utils.find_device('1A86:5523')
        self.assertEqual(device_path, '/dev/tty2')

    @mock.patch(
        'freshroastsr700.utils.list_ports.comports',
        return_value=[
            ['/dev/tty1', 'test_element', '1AB5:5555'],
            ['/dev/tty2', 'test_element', '1A86:5523']])
    def test_find_device_with_device_unavailable(self, mock_comports):
        with self.assertRaises(exceptions.RoasterLookupError):
            utils.find_device('1234:5678')

    def test_seconds_to_float(self):
        self.assertEqual(6.6, utils.seconds_to_float(394))

    def test_seconds_to_float_high(self):
        self.assertEqual(9.9, utils.seconds_to_float(595))

    def test_seconds_to_float_exact(self):
        self.assertEqual(9.9, utils.seconds_to_float(594))
