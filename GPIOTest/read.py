import RPi.GPIO as GPIO
import time
import sys
import pdb

''' Using this file to implement a digital scope so I can debug the type of protocol used between
the main board and the top control board.
'''

def waitForChange(gpioNum):
    ''' Wait for any GPIO to change status before starting the recording.
    Perhaps I should use a callback instead of this.
    '''
    print "Waiting for GPIO change to start recording\n"
    a0 = []
    for gp in gpioNum:
      a0.append(GPIO.input(gp))
    while(1):
      try:
        for i,gp in enumerate(gpioNum):
          if not a0[i] == GPIO.input(gp): 
            print "Detected change in GPIO {}... Starting\n".format(gp)
            return
          time.sleep(.1)
      except KeyboardInterrupt: break
    return

def readGPIO(gpioNum,numMeasures,period,autoTrigger=1):
    ''' Reads a list of GPIOs and returns the values in a matrix with the time in ms as first value.
    '''
    if autoTrigger: waitForChange(gpioNum)
      
    t0 = time.time()
    gpioRead = []
    for i in range(numMeasures):
      try:
        a = [1000*(time.time() - t0)]
        for gp in gpioNum:
          a.append(GPIO.input(gp))
        #print a
        gpioRead.append(a)
      except KeyboardInterrupt: break
      time.sleep(period/4)
    t1 = time.time()
    return gpioRead,t1-t0


if __name__ == "__main__":
    
    numSecs = int(sys.argv[1]) 
    
    GPIO.setmode(GPIO.BCM)
    gpioNum = [4,17,27,22,5,6,13,19]
    # Set GPIOs as inputs.
    for gp in gpioNum:
      GPIO.setup(gp, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    # Scope sampling period.
    samplingRate = 10000
    period = 1.0/samplingRate
  
    numMeasures = numSecs*samplingRate
    # Get recording
    values,elapsed = readGPIO(gpioNum,numMeasures,period)
    print "Sampling rate: {:.0f} kHz\n".format(numMeasures/elapsed/1000)
    # Output values to file.
    with open('scope.txt','w') as f:
      for line in values:
        f.write("{:.1f} ".format(float(line[0])))
        for val in line[1:]:
          f.write("{} ".format(val))
        f.write('\n')
        
        
  

