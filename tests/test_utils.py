# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import unittest
from unittest import mock

from freshroastsr700 import utils
from freshroastsr700 import exceptions
from freshroastsr700.utils import list_ports


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
