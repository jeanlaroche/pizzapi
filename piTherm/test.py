import os
import time

# I'm using this to check that the thermostat always starts the way it should.
while 1:
    print "SIGHUP"
    os.system('sudo killall -SIGHUP gunicorn')
    time.sleep(30)
    # Read the log
    with open('heater.log','r') as fd:
        allLines = fd.readlines()
    # Count the UPDATE TEMP THREAD 1
    ii = 0
    for line in allLines:
        if "UPDATE TEMP THREAD 1" in line: ii += 10
    print ii
    if ii < 30: break
    #