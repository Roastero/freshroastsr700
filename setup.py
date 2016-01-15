# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Mark Spicer
# Made available under the MIT license.

import os
from setuptools import setup
from setuptools import find_packages

from freshroastsr700 import __version__


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()
with open(os.path.join(here, 'requirements.txt')) as f:
    requires = f.read().splitlines()

description = 'A module for interfacing with a FreshRoastSR700 coffee roaster.'

setup(
    name='freshroastsr700',
    version=__version__,
    description=description,
    long_description=long_description,
    url='https://github.com/Roastero/freshroastsr700',
    author='Mark Spicer',
    author_email='mds4680@rit.edu',
    license='MIT',
    packages=find_packages(),
    install_requires=requires)
