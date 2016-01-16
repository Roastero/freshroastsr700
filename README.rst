===============
FreshRoastSR700
===============
.. image:: https://travis-ci.org/Roastero/freshroastsr700.svg?branch=master
    :target: https://travis-ci.org/Roastero/freshroastsr700
.. image:: https://coveralls.io/repos/Roastero/freshroastsr700/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/Roastero/freshroastsr700?branch=master
.. image:: https://readthedocs.org/projects/freshroastsr700/badge/?version=latest
    :target: http://freshroastsr700.readthedocs.org/en/latest/?badge=latest
    :alt: Documentation Status

A Python module to control a FreshRoastSR700 coffee roaster.

Install
-------
.. code-block:: bash
    pip install freshroastsr700

Documentation
-------------
Complete code documentation and a breakdown of the FreshroastSR700 
communication protocol can be found at http://freshroastsr700.readthedocs.org

Develop
-------
.. code-block:: bash
    git clone git@github.com:Roastero/freshroastsr700.git
    cd freshroastsr700
    virtualenv venv -p python3
    source venv/bin/activate
    python setup.py develop

Tests
-----
This module uses tox to run tests and a code linter. Run the commands below in 
the base project directory to install everything needed and run tests on the 
freshroastsr700 module.
.. code-block:: bash
    pip install -r test-requirements.txt
    tox
