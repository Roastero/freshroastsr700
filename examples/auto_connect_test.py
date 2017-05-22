import freshroastsr700
import time
import multiprocessing as mp

if __name__ == "__main__":
	mp.freeze_support()

	roaster = freshroastsr700.freshroastsr700()

	# test auto-connect...
	roaster.auto_connect()

	wait_timeout = time.time() + 40.0
	while not roaster.connected:
		if time.time() > wait_timeout:
			print("Waited for a connection, didn't find one, bailing.")
			exit()
		print("Connection state is %s" % str(roaster.connect_state))
		time.sleep(0.5)

	roaster.fan_speed = 3
	roaster.heat_setting = 1
	roaster.time_remaining = 10
	roaster.roast()

	time.sleep(6.0)

	roaster.fan_speed = 5
	roaster.heat_setting = 0
	roaster.time_remaining = 10
	roaster.cool()

	time.sleep(6.0)

	roaster.idle()

	time.sleep(0.5)

	roaster.disconnect()

	time.sleep(2.0)

	# test a re-connect after a successful session
	roaster.connect()

	roaster.fan_speed = 7
	roaster.heat_setting = 1
	roaster.time_remaining = 10
	roaster.roast()

	time.sleep(6.0)

	roaster.fan_speed = 9
	roaster.heat_setting = 0
	roaster.time_remaining = 10
	roaster.cool()

	time.sleep(6.0)

	roaster.idle()

	time.sleep(0.5)

	roaster.disconnect()
