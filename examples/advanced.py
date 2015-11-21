# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import time
import freshroastsr700


class Roaster(object):
    def __init__(self):
        """Creates a freshroastsr700 object passing in methods included in this
        class."""
        self.roaster = freshroastsr700.freshroastsr700(
            self.update_data, self.next_state, thermostat=True)

    def update_data(self):
        """This is a method that will be called every time a packet is opened
        from the roaster."""
        print("Current Temperature:", self.roaster.current_temp)

    def next_state(self):
        """This is a method that will be called when the time remaining ends.
        The current state can be: roasting, cooling, idle, sleeping, connecting,
        or unkown."""
        if(self.roaster.get_roaster_state() == 'roasting'):
            self.roaster.time_remaining = 20
            self.roaster.cool()
        elif(self.roaster.get_roaster_state() == 'cooling'):
            self.roaster.idle()


# Create a roaster object.
r = Roaster()

# Conenct to the roaster.
r.roaster.auto_connect()

# Wait for the roaster to be connected.
while(r.roaster.connected is False):
    print("Please connect your roaster...")
    time.sleep(1)

# Set variables.
r.roaster.target_temp = 320
r.roaster.fan_speed = 9
r.roaster.time_remaining = 40

# Begin roasting.
r.roaster.roast()

# This ensures the example script does not end before the roast.
time.sleep(80)

# Disconnect from the roaster.
r.roaster.disconnect()
