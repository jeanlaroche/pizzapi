import time
import sys
import select
import multiprocessing
import readTemp as rt

def myDisp(thisString):
# A special display that goes back to the beginning of the line.
	back = "\b"*(len(thisString)+1)
	print thisString + back,

# import curses
# def main(win):
    # win.nodelay(True)
    # key=""
    # win.clear()                
    # win.addstr("Detected key:")
    # while 1:          
        # try:                 
           # key = win.getkey()         
           # win.clear()                
           # win.addstr("Detected key:")
           # win.addstr(str(key)) 
           # if key == os.linesep:
              # break           
        # except Exception as e:
           # # No input   
           # pass         
# curses.wrapper(main)

def heardEnter():
	# Function to detect a keepress. Apparently I could also use import curses, a standard packing in linux.
    i,o,e = select.select([sys.stdin],[],[],0.0001)
    for s in i:
        if s == sys.stdin:
            input = sys.stdin.readline()
            return True
    return False

if __name__ == "__main__":
	rt.setup()
	while 1:
		try:
			# This is the main loop. It simply displays the current temperature, just the way the top panel does it.
			tempValue,heater,avSampPerClock = rt.readTemperature()[1:]
			myDisp ("Temperature: {:}F -- Heater: {} -- Av. samp. per clock {:.2f}".format(tempValue,heater,avSampPerClock))
			# myDisp('Current time: {:.3f}'.format(t2))
			# Check whether we pressed Enter
			if heardEnter():
				# Do the equivalent of pressing the button, then keep on going
				rt.pressTempAdjust()
		except KeyboardInterrupt: break
		except multiprocessing.TimeoutError:
			myDisp("Time out error!")
			break
	rt.tearDown()
	
