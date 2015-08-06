# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import os
from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'requirements.txt')) as f:
    requires = f.read().splitlines()

setup(
    name='freshroastsr700',
    version='0.1',
    description=
        'A module for interfacing with a FreshRoastSR700 coffee roaster.',
    url='https://github.com/Roastero/freshroastsr700',
    author='Roastero',
    author_email='admin@roastero.com',
    license='GPLv3',
    packages=['freshroastsr700'],
    install_requires=requires)
