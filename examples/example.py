# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import time
import freshroastsr700


def next_state(roaster, current_state):
    """This is a function that will be called when the time remaining ends. The
    current state can be: roasting, cooling, idle, or sleeping."""
    if(current_state == 'roasting'):
        roaster.time_remaining = 20
        roaster.cool()
    elif(current_state == 'cooling'):
        roaster.idle()

# Create a roaster object.
roaster = freshroastsr700.freshroastsr700(next_state)

# Conenct to the roaster.
roaster.connect()

# Set variables.
roaster.heat_setting = 3
roaster.fan_speed = 9
roaster.time_remaining = 20

# Begin roasting.
roaster.roast()

# This ensures the example script does not end before the roast.
time.sleep(60)

# Disconnect from the roaster.
roaster.disconnect()
