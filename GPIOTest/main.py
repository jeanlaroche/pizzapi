import time
import sys
import select
import multiprocessing
import readTemp as rt
import termios,tty

def myDisp(thisString):
# A special display that goes back to the beginning of the line.
	back = "\b"*(len(thisString)+1)
	print thisString + back

class NonBlockingConsole(object):
	def __enter__(self):
		self.old_settings = termios.tcgetattr(sys.stdin)
		tty.setcbreak(sys.stdin.fileno())
		return self

	def __exit__(self, type, value, traceback):
		termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

	def get_data(self):
		if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
			return sys.stdin.read(1)
		return ''

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
	with NonBlockingConsole() as nbc:
		while 1:
			try:
				# Check whether we pressed Enter
				key = nbc.get_data()
				if key == 'q': break
				if not key == '':
					# Do the equivalent of pressing the button, then keep on going
					rt.pressTempAdjust()
				# This is the main loop. It simply displays the current temperature, just the way the top panel does it.
				# tempValue,heater,avSampPerClock = rt.readTemperature()[1:]
				# myDisp ("Temperature: {:}F -- Heater: {} -- Av. samp. per clock {:.2f}".format(tempValue,heater,avSampPerClock))
				# myDisp('Current time: {:.3f}'.format(t2))
				time.sleep(.2)
			except KeyboardInterrupt: break
			except multiprocessing.TimeoutError:
				myDisp("Time out error!")
	rt.tearDown()
	
