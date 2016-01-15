# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Mark Spicer
# Made available under the MIT license.

import time
import freshroastsr700


# Create a roaster object.
roaster = freshroastsr700.freshroastsr700()

# Conenct to the roaster.
roaster.connect()

# Set variables.
roaster.heat_setting = 3
roaster.fan_speed = 9
roaster.time_remaining = 20

# Begin roasting.
roaster.roast()

# This ensures the example script does not end before the roast.
time.sleep(30)

# Disconnect from the roaster.
roaster.disconnect()
