# -*- coding: utf-8 -*-
# Roastero, released under GPLv3

import time
import freshroastsr700


# Create a roaster object.
roaster = freshroastsr700.freshroastsr700()

# Conenct to the roaster.
roaster.connect()

# Set variables.
roaster.heat_setting = 3
roaster.fan_speed = 9
roaster.time_remaining = 9.9

# Begin roasting.
roaster.roast()
time.sleep(10)

# IMPORTANT: Cool down the roaster when finished roasting.
roaster.cool()
time.sleep(10)

# Set the roaster back to the inital state.
roaster.idle()
time.sleep(1)

# Disconnect from the roaster.
roaster.disconnect()
