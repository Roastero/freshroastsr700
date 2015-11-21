# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import os
from setuptools import setup
from setuptools import find_packages


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()
with open(os.path.join(here, 'requirements.txt')) as f:
    requires = f.read().splitlines()

description = 'A module for interfacing with a FreshRoastSR700 coffee roaster.'

setup(
    name='freshroastsr700',
    version='0.2',
    description=description,
    long_description=long_description,
    url='https://github.com/Roastero/freshroastsr700',
    author='Roastero',
    author_email='admin@roastero.com',
    license='GPLv3',
    packages=find_packages(),
    install_requires=requires)
