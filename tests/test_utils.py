# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import unittest

from freshroastsr700 import utils


class TestUtils(unittest.TestCase):
    def test_frange_works(self):
        accepted_range = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        generated_range = [value for value in utils.frange(0.0, 0.9, 0.1, 1)]

        self.assertEqual(accepted_range, generated_range)
