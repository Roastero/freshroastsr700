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

Usage
=====

.. code:: python

  import time
  import multiprocessing
  import freshroastsr700

  # freshroastsr700 uses multiprocessing under the hood.
  # call multiprocessing.freeze_support() if you intend to
  # freeze your app for packaging.
  multiprocessing.freeze_support()

  # Create a roaster object.
  roaster = freshroastsr700.freshroastsr700()

  # Conenct to the roaster.
  roaster.connect()

  # Set roasting variables.
  roaster.heat_setting = 3
  roaster.fan_speed = 9
  roaster.time_remaining = 20

  # Begin roasting.
  roaster.roast()

  # This ensures the example script does not end before the roast.
  time.sleep(30)

  # Disconnect from the roaster.
  roaster.disconnect()

API & Documentation
===================
Complete code documentation and a breakdown of the FreshroastSR700 communication protocol can be found at freshroastsr700.readthedocs.org_. The Fresh Roast SR700 can be purchased directly from the manufacturer at homeroastingsupplies.com_.

.. _freshroastsr700.readthedocs.org: http://freshroastsr700.readthedocs.org
.. _homeroastingsupplies.com: http://homeroastingsupplies.com/product/fresh-roast-sr700/

Installation
============
The latest release of this package can be installed by running:

::

    pip install freshroastsr700

Version History
===============
Version 0.2.1 - March 2017
--------------------------
 - Resolves issue #20 by managing hardware discovery logic in the
   comm process, eliminating the need for the thread heretofore
   associated with auto_connect.  Openroast 1.2 (currently in development)
   now operates properly in Windows 10 64-bit, with this fix.

Version 0.2.0 - March 2017
--------------------------
 - Completely rewritten PID control for tighter tracking against target
   temperature (when freshroastsr700 is instantiated with thremostat=True).
 - Callback functions for update_data_func and state_transition_func now
   called from a thread belonging to the process that instantiated freshroastsr700.  This was necessary for Openroast version 1.2
   code refactoring.
 - Reduced processor load for PID control as part of code refactoring.

Version 0.1.1 - Dec 28 2017
---------------------------
 - Added support for python 2.7.

Version 0.1.0
-------------
 - (no notes)

License
=======
MIT License. Please refer to LICENSE in this package for details.
