# FreshRoastSR700
[![Build Status](https://travis-ci.org/Roastero/freshroastsr700.svg?branch=master)](https://travis-ci.org/Roastero/freshroastsr700)
[![Coverage Status](https://coveralls.io/repos/Roastero/freshroastsr700/badge.svg?branch=master&service=github)](https://coveralls.io/github/Roastero/freshroastsr700?branch=master)

A python package to interface with a FreshRoastSR700 coffee roaster.

##  FreshRoastSR700 Communication Protocol
All of the communication between the FreshRoastSR700 and the computer are 
happening over serial. The device contains a USB to serial adapter that uses 
the CH341 chipset. With this, it creates a virtual serial port that the program 
and roaster communicate over. Each of them send 14 byte packets back and forth 
between each other. Below is the basic packet structure of the serial 
communications between the devices.

|Header|Temperature Unit|Flags|Current State|Fan Speed|Time Remaining|Heat Setting|Current Temperature|Footer|
|-------------|---|-----|-------|---------|-----|------------|-------------------|------|
|2 bytes|2 bytes|1 byte|2 bytes|1 byte|1 byte|1 byte|2 bytes|2 bytes|

An example packet would look like the following:

|Header|Temperature Unit|Flags|Current State|Fan Speed|Time Remaining|Heat Setting|Current Temperature|Footer|
|-------------|---|-----|-------|---------|-----|------------|-------------------|------|
|AA AA | 61 74 | 63 | 02 01 | 01 | 32 | 01 | 00 00 | AA FA |

### Packet fields

#### Header (2 bytes)
This field is 2 bytes and is almost always `AA AA`. When initializing 
communications with the roaster, the computer sends `AA 55`.

#### Temperature Unit (2 bytes)
The next 2 bytes are used to set the unit (Celsius or Fahrenheit) of the 
temperature being returned from the roaster. For Fahrenheit, this field should 
be `61 74`.

#### Flags (1 byte)
This field of the packet is used to determine what type of packet is being sent 
or received.

`63` - The packet was sent by the computer.

`00` - The packet was sent by the roaster.

`A0` - The current settings on the roaster that had been set manually.

`AA` - A beginning or middle line of a previously run recipe that had been 
saved to the roaster.

`AF` - Last line of a previously run recipe that had been saved to the roaster.

#### Current State (2 bytes)
This section controls the current state of the roaster. This field is 
responsible for making the roaster start and stop.

`02 01` - Idle (Shows current timer and fan speed values)

`04 02` - Roasting

`04 04` - Cooling

`08 01` - Sleeping (Displays "-" in both fan speed and timer fields on the 
roaster)

#### Fan Speed (1 byte)
This field is the current fan speed in hex. Below is a list of valid values for 
this field.

`01`,`02`,`03`,`04`,`05`,`06`,`07`,`08`,`09`

#### Time Remaining (1 byte)
This field is the time remaining in hex. The time remaining is a decimal 
representation of time as displayed on the roaster. For example, one minute and 
thirty seconds would appear as 1.5 on the roaster and should be set as `0F` in 
hex. Additionally, five minutes and fifty-four seconds would be represented 
as 5.9 on the roaster and `3B` in hex.

#### Heat Setting (1 byte)
This field is the heat setting for the roaster. This value will not cause the 
roaster to start roasting. It only dictates what the roaster will do once it 
begins. Below is a list of valid values.

`00` - No Heat (Cooling)

`01` - Low Heat

`02` - Medium Heat

`03` - High Heat

#### Current Temperature (2 bytes)
This field is the current temperature as recorded by the roaster encoded in 
hex. When the roaster does not read a temperature of 150°F or higher, it sends 
the following hex: `FF 00`. If the temperature is higher than 150°F, the 
temperature is sent encoded in hex. For example, 352°F is `01 60`.

#### Footer (2 bytes)
This field signifies the end of a packet and is always `AA FA`. 

### Packet Sequences
The FreshRoastSR700 has a distinct packet sequence that must be followed in 
order to communicate with the roaster.

To start off, every communication between the roaster and the computer is 
initiated by the computer. It is initiated with a packet that looks like the 
packet below.

`AA 55 61 74 63 00 00 00 00 00 00 00 AA FA`

This packet is a blank packet with the header set to `55`. This then signals 
the roaster to send back the last recipe that had been loaded onto the roaster. 
Below is an example of the data that roaster would send back.

`AA AA 61 74 A0 00 00 09 3B 02 00 00 AA FA` -- Manual setting currently on the 
roaster.

`AA AA 61 74 AA 00 00 09 03 03 00 00 AA FA` -- First line of the recipe 
currently on the roaster.

`AA AA 61 74 AA 00 00 09 01 02 00 00 AA FA` -- Second line of the recipe 
currently on the roaster.

`AA AA 61 74 AF 00 00 09 1C 00 00 00 AA FA` -- Last line of the recipe 
currently on the roaster.

The roaster sends the above packets one right after another. It doesn't wait 
for the computer to respond until after the last line of sequence is sent. The 
last packet sent is denoted by `AF` in the flags field.

After this, the computer sends back the heat setting, fan speed, and time 
remaining it wants the roaster to be set to. This is all sent in a single 
packet like the following.

`AA AA 61 74 63 02 01 01 3B 01 00 00 AA FA` -- heat=low, fan speed=1, time=5.9
minutes

The roaster then sends back the current settings including the current 
temperature of the roaster if it's 150°F or higher. The response packet would 
look like the following.

`AA AA 61 74 00 02 01 01 32 01 FF 00 AA FA`

This continues indefinitely until the connection is closed. A packet should be 
sent from the computer every quarter of a second, and no sooner. When the 
roaster should begin roasting, set the current state to roasting. The roaster 
cannot go directly to cooling, and must be first set to roasting.
