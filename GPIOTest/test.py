import RPi.GPIO as GPIO
import time


# Function to evaluate the sampling rate for reading GPIOs.
def testSpeed():
  GPIO.setmode(GPIO.BCM)
  gpioNum = [4,5,6,7,8,9,10,11]
  for gp in gpioNum:
    GPIO.setup(gp, GPIO.IN, pull_up_down=GPIO.PUD_UP)
  
  time1 = time.time()
  for i in range(10000000):
    try:
      for gp in gpioNum:
            a = GPIO.input(gp)
    except KeyboardInterrupt: break
  
  time2=time.time()
  print "{:} K reads in {:.3}s or {:.0f}kHz\n".format((i+1)/1000,time2-time1,i/(time2-time1)/1000)



# Two function to make a LED glow, the hard way.
# This lights up the LED for 10ms at perc of full brightness
def foo(perc):
  perc = perc*perc*perc
  if perc < 0.0005: perc = 0.0005
  for ii in range(10):
   GPIO.output(4,1)
   time.sleep(0.002*perc)
   GPIO.output(4,0)
   time.sleep(0.002*(1-perc))

# This calls foo while varying the brightness!
def faa(speed):
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(4, GPIO.OUT)
  N = int(100/speed)
  while 1:
    for ii in range(N):
      foo(float(ii)/N)
    for ii in range(N):
      foo(float(N-ii)/N)
