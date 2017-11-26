from ctypes import *

tslib = cdll.LoadLibrary("libts-0.0.so.0")

class tsdev(Structure):
	pass

class timeval(Structure):
	_fields_ = [("tv_sec", c_long),
		("tv_usec", c_long)]

class ts_sample(Structure):
	_fields_ = [("x", c_int),
		("y", c_int),
		("pressure", c_uint),
		("tv", timeval)]

ts_read_raw = tslib.ts_read_raw
ts_read_raw.restype = c_int
ts_read_raw.argtypes = [POINTER(tsdev), POINTER(ts_sample), c_int]

ts_read = tslib.ts_read
ts_read.restype = c_int
ts_read.argtypes = [POINTER(tsdev), POINTER(ts_sample), c_int]

ts_open = tslib.ts_open
ts_open.restype = POINTER(tsdev)
ts_open.argtypes = [c_char_p, c_int]

ts_close = tslib.ts_close
ts_close.restype = c_int
ts_close.argtypes = [POINTER(tsdev)]

ts_config = tslib.ts_config
ts_config.restype = c_int
ts_config.argtype = [POINTER(tsdev)]


ts = ts_open("/dev/input/event2", 0)
if ts == 0:
	exit("ts_open failed")

if ts_config(ts):
	exit("ts_config failed")

def read(ts):
	s = ts_sample()
	while True:
		if ts_read(ts, byref(s), 1) < 0:
			exit("ts_read_raw failed")
		if s.pressure != 0:
			print s.x,s.y


read(ts)

def get_xy(ts):
	samples_x = list()
	samples_y = list()

	s = ts_sample()

	# read until pressed
	while True:
		if ts_read_raw(ts, byref(s), 1) < 0:
			exit("ts_read_raw failed")
		if s.pressure != 0:
			break

	# read until 128 values are gathered or no longer pressed
	for i in range(128):
		if ts_read_raw(ts, byref(s), 1) < 0:
			exit("ts_read_raw failed")
		if s.pressure == 0:
			break
		else:
			samples_x.append(s.x)
			samples_y.append(s.y)

	samples_x.sort()
	samples_y.sort()

	middle = i/2

	# return the median
	if i%2 == 0:
		return ((samples_x[middle-1]+samples_x[middle])/2,
			(samples_y[middle-1]+samples_y[middle])/2)
	else:
		return (samples_x[middle], samples_y[middle])

cal = {(50, 50): get_xy(ts),
	(480-50, 50): get_xy(ts),
	(480-50, 640-50): get_xy(ts),
	(50, 640-50): get_xy(ts),
	(480/2, 640/2): get_xy(ts)}

scaling = 65536.0

#print cal

# get sums for matrix
n = 5.0
x = sum([_x_ for _x_, _y_ in cal.values()])
y = sum([_y_ for _x_, _y_ in cal.values()])
x2 = sum([_x_*_x_ for _x_, _y_ in cal.values()])
y2 = sum([_y_*_y_ for _x_, _y_ in cal.values()])
xy = sum([_x_*_y_ for _x_, _y_ in cal.values()])

#print n, x, y, x2, y2, xy

# get determinant
det = n*(x2*y2 - xy*xy) + x*(xy*y - x*y2) + y*(x*xy - y*x2)

#print det

# check determinant
if ((det < 0.1) and (det > -0.1)):
	exit("determinant is too small")

# calculate inverse matrix
a = (x2*y2 - xy*xy)/det
b = (xy*y - x*y2)/det
c = (x*xy - y*x2)/det
e = (n*y2 - y*y)/det
f = (x*y - n*xy)/det
i = (n*x2 - x*x)/det

#print a, b, c, e, f, i

# get sums for x calibration
z = sum([xfb for xfb, yfb in cal.keys()])
zx = sum([xfb*x for (xfb, yfb), (x, y) in cal.items()])
zy = sum([xfb*y for (xfb, yfb), (x, y) in cal.items()])

#print z, zx, zy

print int((b*z + e*zx + f*zy)*scaling), int((c*z + f*zx + i*zy)*scaling), int((a*z + b*zx + c*zy)*scaling)

# get sums for y calibration
z = sum([yfb for xfb, yfb in cal.keys()])
zx = sum([yfb*x for (xfb, yfb), (x, y) in cal.items()])
zy = sum([yfb*y for (xfb, yfb), (x, y) in cal.items()])

#print z, zx, zy

print int((b*z + e*zx + f*zy)*scaling), int((c*z + f*zx + i*zy)*scaling), int((a*z + b*zx + c*zy)*scaling)

print int(scaling)

ts_close(ts)


