# -*- coding: utf-8 -*-
# Roastero, released under GPLv3


def frange(start, stop, step, precision):
    """A generator that will generate a range of floats."""
    value = start
    while round(value, precision) < stop:
        yield round(value, precision)
        value += step
