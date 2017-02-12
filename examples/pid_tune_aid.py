# -*- coding: utf-8 -*-

import time
import datetime
import freshroastsr700


class Roaster(object):
    def __init__(self, kp=0.06, ki=0.0075, kd=0.01):
        """Creates a freshroastsr700 object passing in methods included in this
        class. Set the PID values above to set them in the freshroastsr700
        object."""
        self.roaster = freshroastsr700.freshroastsr700(
            self.update_data,
            self.next_state,
            thermostat=True,
            kp=kp,
            ki=ki,
            kd=kd)
        # test vector for driving sr700
        # quick recipe simulation
        # self.recipe = [
        #     {
        #         'time_remaining': 60,
        #         'target_temp': 350,
        #         'fan_speed': 9,
        #         'state': 'roasting'
        #     },
        #     {
        #         'time_remaining': 60,
        #         'target_temp': 390,
        #         'fan_speed': 5,
        #         'state': 'roasting'
        #     },
        #     {
        #         'time_remaining': 30,
        #         'target_temp': 420,
        #         'fan_speed': 5,
        #         'state': 'roasting'
        #     },
        #     {
        #         'time_remaining': 60,
        #         'target_temp': 450,
        #         'fan_speed': 5,
        #         'state': 'roasting'
        #     },
        #     {
        #         'time_remaining': 60,
        #         'target_temp': 480,
        #         'fan_speed': 3,
        #         'state': 'roasting'
        #     },
        #     {
        #         'time_remaining': 60,
        #         'target_temp': 500,
        #         'fan_speed': 3,
        #         'state': 'roasting'
        #     },
        #     {
        #         'time_remaining': 60,
        #         'target_temp': 150,
        #         'fan_speed': 9,
        #         'state': 'cooling'
        #     },
        #     {
        #         'time_remaining': 1,
        #         'target_temp': 150,
        #         'fan_speed': 1,
        #         'state': 'idle'
        #     }
        # ]
        # for dialing in pid params - 3 min. short cycle
        self.recipe = [
            {
                'time_remaining': 60,
                'target_temp': 300,
                'fan_speed': 9,
                'state': 'roasting'
            },
            {
                'time_remaining': 60,
                'target_temp': 350,
                'fan_speed': 5,
                'state': 'roasting'
            },
            {
                'time_remaining': 60,
                'target_temp': 400,
                'fan_speed': 5,
                'state': 'roasting'
            },
            {
                'time_remaining': 60,
                'target_temp': 450,
                'fan_speed': 4,
                'state': 'roasting'
            },
            {
                'time_remaining': 30,
                'target_temp': 150,
                'fan_speed': 9,
                'state': 'cooling'
            },
            {
                'time_remaining': 1,
                'target_temp': 150,
                'fan_speed': 1,
                'state': 'idle'
            }
        ]
        # to set up process to begin, call next state to load first state
        self.active_recipe_item = -1
        # open file to write temps in CSV format
        self.file = open("sr700_pid_tune.csv", "w")
        self.file.write("Time,crntTemp,targetTemp,heaterLevel\n")
        # get start timestamp
        self.start_time = datetime.datetime.now()

    def __del__(self):
        self.file.close()

    def update_data(self):
        """This is a method that will be called every time a packet is opened
        from the roaster."""
        time_elapsed = datetime.datetime.now() - self.start_time
        crntTemp = self.roaster.current_temp
        targetTemp = self.roaster.target_temp
        heaterLevel = self.roaster.heater_level
        # print(
        #     "Time: %4.6f, crntTemp: %d, targetTemp: %d, heaterLevel: %d" %
        #     (time_elapsed.total_seconds(), crntTemp, targetTemp, heaterLevel))
        self.file.write(
            "%4.6f,%d,%d,%d\n" %
            (time_elapsed.total_seconds(), crntTemp, targetTemp, heaterLevel))

    def next_state(self):
        """This is a method that will be called when the time remaining ends.
        The current state can be: roasting, cooling, idle, sleeping, connecting,
        or unkown."""
        self.active_recipe_item += 1
        if self.active_recipe_item >= len(self.recipe):
            # we're done!
            return
        # show state step on screen
        print("--------------------------------------------")
        print("Setting next process step: %d" % self.active_recipe_item)
        print("time:%d, target: %ddegF, fan: %d, state: %s" %
              (self.recipe[self.active_recipe_item]['time_remaining'],
               self.recipe[self.active_recipe_item]['target_temp'],
               self.recipe[self.active_recipe_item]['fan_speed'],
               self.recipe[self.active_recipe_item]['state']
               ))
        print("--------------------------------------------")
        # set values for next state
        self.roaster.time_remaining = (
            self.recipe[self.active_recipe_item]['time_remaining'])
        self.roaster.target_temp = (
            self.recipe[self.active_recipe_item]['target_temp'])
        self.roaster.fan_speed = (
            self.recipe[self.active_recipe_item]['fan_speed'])
        # set state
        if(self.recipe[self.active_recipe_item]['state'] == 'roasting'):
            self.roaster.roast()
        elif(self.recipe[self.active_recipe_item]['state'] == 'cooling'):
            self.roaster.cool()
        elif(self.recipe[self.active_recipe_item]['state'] == 'idle'):
            self.roaster.idle()
        elif(self.recipe[self.active_recipe_item]['state'] == 'cooling'):
            self.roaster.sleep()

    def recipe_total_time(self):
        total_time = 0
        for step in self.recipe:
            total_time += step['time_remaining']
        return total_time


if __name__ == "__main__":

    # Create a roaster object.
    r = Roaster()

    # Conenct to the roaster.
    r.roaster.auto_connect()

    # Wait for the roaster to be connected.
    while(r.roaster.connected is False):
        print("Please connect your roaster...")
        time.sleep(1)

    # get the roast started
    r.roaster.roast()

    # This ensures the example script does not end before the roast.
    time.sleep(10+r.recipe_total_time())

    # Disconnect from the roaster.
    r.roaster.disconnect()
