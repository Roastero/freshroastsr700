# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Mark Spicer
# Made available under the MIT license.

from setuptools import setup
from setuptools import find_packages


description = 'A module for interfacing with a FreshRoastSR700 coffee roaster.'

setup(
    name='freshroastsr700',
    version='0.0.5',
    description=description,
    url='https://github.com/Roastero/freshroastsr700',
    author='Mark Spicer',
    author_email='mds4680@rit.edu',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'pyserial>=3.0.1'])
