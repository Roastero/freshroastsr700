# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Mark Spicer
# Made available under the MIT license.

import os
from setuptools import setup
from setuptools import find_packages


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    long_description = f.read()

setup(
    name='freshroastsr700',
    version='0.1.1',
    description='A Python module to control a FreshRoastSR700 coffee roaster.',
    long_description=long_description,
    url='https://github.com/Roastero/freshroastsr700',
    author='Mark Spicer, Caleb Coffee',
    author_email='mds4680@rit.edu',
    maintainer='Mark Spicer',
    maintainer_email='mds4680@rit.edu',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'pyserial>=3.0.1'
    ]
)
