Release Notes
=============

Version 0.2.0 - March 2017
--------------------------

Completely rewritten PID control for tighter tracking against target temperature (when freshroastsr700 is instantiated with thremostat=True).
Callback functions for update_data_func and state_transition_func now called from a thread belonging to the process that instantiated freshroastsr700. This was necessary for Openroast version 1.2 code refactoring.
Reduced processor load for PID control as part of code refactoring.

Version 0.1.1 - Dec 28 2017
---------------------------

Added support for python 2.7.

Version 0.1.0
-------------

(no notes)

Version 0.0.6
-------------

(no notes)
