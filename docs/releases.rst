Release Notes
=============

Version 0.2.2 - April 2017
--------------------------
Resolves issue #22, 23, 24 and 25.  Added logic to handle hardware
connects and hardware disconnects properly in all supported OSes.  Software
now supports multiple connect()-disconnect() cycles using the same
freshroastsrs700 object instance.

Version 0.2.1 - March 2017
--------------------------
Resolves issue #20 by managing hardware discovery logic in the
comm process, eliminating the need for the thread heretofore
associated with auto_connect.  Openroast 1.2 (currently in development)
now operates properly in Windows 10 64-bit, with this fix.

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
