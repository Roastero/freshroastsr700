# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import time
import freshroastsr700


def update_data(roaster):
    """This is a function that will be called every time a packet is opened
    from the roaster."""
    print("Current Temperature:", roaster.current_temp)


def next_state(roaster, current_state):
    """This is a function that will be called when the time remaining ends. The
    current state can be: roasting, cooling, idle, or sleeping."""
    if(current_state == 'roasting'):
        roaster.time_remaining = 20
        roaster.cool()
    elif(current_state == 'cooling'):
        roaster.idle()


# Create a roaster object.
roaster = freshroastsr700.freshroastsr700(
    update_data, next_state, thermostat=True)

# Conenct to the roaster.
roaster.auto_connect()

# Wait for the roaster to be connected.
while(roaster.connected is False):
    print("Please connect your roaster...")
    time.sleep(1)

# Set variables.
roaster.target_temp = 320
roaster.fan_speed = 9
roaster.time_remaining = 40

# Begin roasting.
roaster.roast()

# This ensures the example script does not end before the roast.
time.sleep(80)

# Disconnect from the roaster.
roaster.disconnect()
